from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .encryption import read_encrypted, safe_filename, store_bytes
from .models import (
    AccessLog,
    Appointment,
    Article,
    Complaint,
    DoctorProfile,
    ForumComment,
    ForumPost,
    PatientProfile,
    PeriodLog,
    PregnancyLog,
    Prescription,
    Rating,
    Reminder,
    Report,
    Slot,
    User,
)
from .permissions import IsAdminRole, IsApprovedDoctor, IsPatient
from .serializers import (
    AccessLogSerializer,
    AdminAppointmentSerializer,
    ArticleDetailSerializer,
    ArticleSerializer,
    BookSerializer,
    ComplaintSerializer,
    DoctorCardSerializer,
    DoctorDetailSerializer,
    EmailTokenObtainPairSerializer,
    ForumPostDetailSerializer,
    ForumPostSerializer,
    PeriodSerializer,
    RegisterSerializer,
    ReminderSerializer,
    ReportSerializer,
    SlotCreateSerializer,
    SlotSerializer,
    UserSerializer,
    AppointmentSerializer,
)
from .services import (
    SUGGEST_DISCLAIMER,
    add_booking_reminders,
    create_slots,
    doctor_has_patient,
    log_access,
    pregnancy_summary,
    refresh_period_reminder,
    refresh_pregnancy_reminder,
    suggest_doctors,
    with_stats,
)


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": UserSerializer(user).data,
    }


def scoped_appointments(user):
    qs = Appointment.objects.select_related("slot", "doctor__user", "patient")
    if user.role == User.Role.PATIENT:
        return qs.filter(patient=user)
    if user.role == User.Role.DOCTOR:
        try:
            return qs.filter(doctor=user.doctor_profile)
        except DoctorProfile.DoesNotExist:
            return qs.none()
    if user.role == User.Role.ADMIN:
        return qs
    return qs.none()


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            email = (request.data.get("email") or "").strip().lower()
            user = User.objects.filter(email=email).first()
            if user:
                log_access(user, "login", "signed in", request)
        return response


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if request.data.get("role") == User.Role.ADMIN:
            return Response({"role": ["Admin accounts are not open for signup."]}, status=400)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_access(user, "register", user.role, request)
        return Response(tokens_for(user), status=201)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        for field in ("first_name", "last_name", "phone", "forum_name"):
            if field in request.data:
                setattr(user, field, str(request.data.get(field) or "")[:150])
        user.save()
        if user.role == User.Role.PATIENT:
            profile, _ = PatientProfile.objects.get_or_create(user=user)
            if "city" in request.data:
                profile.city = str(request.data.get("city") or "")[:80]
            if "cycle_length" in request.data:
                try:
                    length = int(request.data["cycle_length"])
                except (TypeError, ValueError):
                    return Response({"cycle_length": ["Enter a number."]}, status=400)
                if not 15 <= length <= 60:
                    return Response({"cycle_length": ["Use a cycle length from 15 to 60 days."]}, status=400)
                profile.cycle_length = length
            if "period_length" in request.data:
                try:
                    length = int(request.data["period_length"])
                except (TypeError, ValueError):
                    return Response({"period_length": ["Enter a number."]}, status=400)
                if not 1 <= length <= 10:
                    return Response({"period_length": ["Use a period length from 1 to 10 days."]}, status=400)
                profile.period_length = length
            profile.save()
            refresh_period_reminder(user)
        return Response(UserSerializer(user).data)


class DoctorList(APIView):
    def get(self, request):
        qs = with_stats(DoctorProfile.objects.filter(is_approved=True, declined=False))
        specialty = (request.query_params.get("specialty") or "").strip()
        query = (request.query_params.get("q") or "").strip()
        day = (request.query_params.get("date") or "").strip()
        min_rating = request.query_params.get("min_rating")
        if specialty:
            qs = qs.filter(specialty__iexact=specialty)
        if query:
            qs = qs.filter(
                Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(clinic_name__icontains=query)
                | Q(treats__icontains=query)
                | Q(specialty__icontains=query)
            )
        if day:
            open_ids = Slot.objects.filter(date=day, is_booked=False).values("doctor_id")
            qs = qs.filter(id__in=open_ids)
        if min_rating:
            try:
                qs = qs.filter(rating_avg__gte=float(min_rating))
            except ValueError:
                return Response({"min_rating": ["Enter a number from 1 to 5."]}, status=400)
        qs = qs.order_by("-rating_avg", "user__first_name")
        specialties = sorted(
            DoctorProfile.objects.filter(is_approved=True, declined=False)
            .values_list("specialty", flat=True)
            .distinct()
        )
        return Response(
            {
                "specialties": specialties,
                "doctors": DoctorCardSerializer(qs, many=True, context={"request": request}).data,
            }
        )


class DoctorDetail(APIView):
    def get(self, request, pk):
        qs = with_stats(DoctorProfile.objects.filter(is_approved=True, declined=False))
        doctor = get_object_or_404(qs, pk=pk)
        return Response(DoctorDetailSerializer(doctor, context={"request": request}).data)


class DoctorSuggest(APIView):
    def post(self, request):
        symptoms = (request.data.get("symptoms") or "").strip()
        if len(symptoms) < 3:
            return Response(
                {"symptoms": ["Type a few words about what you are feeling, or search without a suggestion."]},
                status=400,
            )
        payload = suggest_doctors(symptoms)
        reasons = {doctor.id: reason for doctor, reason, _strength in payload["results"]}
        doctors = [doctor for doctor, _reason, _strength in payload["results"]]
        return Response(
            {
                "disclaimer": payload["disclaimer"] or SUGGEST_DISCLAIMER,
                "fallback": payload["fallback"],
                "message": payload["message"],
                "matched_specialties": payload["matched_specialties"],
                "doctors": DoctorCardSerializer(
                    doctors, many=True, context={"request": request, "reasons": reasons}
                ).data,
            }
        )


class DoctorMe(APIView):
    def get(self, request):
        if request.user.role != User.Role.DOCTOR:
            return Response({"detail": "Only a gynecologist has this profile."}, status=403)
        try:
            profile = request.user.doctor_profile
        except DoctorProfile.DoesNotExist:
            return Response({"detail": "Doctor profile is missing."}, status=404)
        data = DoctorDetailSerializer(with_stats(DoctorProfile.objects.filter(pk=profile.pk)).get(), context={"request": request}).data
        return Response(data)

    def put(self, request):
        if request.user.role != User.Role.DOCTOR:
            return Response({"detail": "Only a gynecologist can edit this profile."}, status=403)
        profile = request.user.doctor_profile
        for field, limit in (
            ("specialty", 80),
            ("qualifications", 200),
            ("bio", 2000),
            ("clinic_name", 160),
            ("clinic_address", 240),
            ("treats", 300),
        ):
            if field in request.data:
                setattr(profile, field, str(request.data.get(field) or "")[:limit])
        if "fee" in request.data:
            try:
                fee = int(request.data["fee"])
            except (TypeError, ValueError):
                return Response({"fee": ["Enter a fee in rupees."]}, status=400)
            if fee < 0 or fee > 20000:
                return Response({"fee": ["Use a fee from 0 to 20000."]}, status=400)
            profile.fee = fee
        if "experience_years" in request.data:
            try:
                years = int(request.data["experience_years"])
            except (TypeError, ValueError):
                return Response({"experience_years": ["Enter a number."]}, status=400)
            if years < 0 or years > 80:
                return Response({"experience_years": ["Enter years from 0 to 80."]}, status=400)
            profile.experience_years = years
        profile.save()
        user = request.user
        for field in ("first_name", "last_name", "phone"):
            if field in request.data:
                setattr(user, field, str(request.data.get(field) or "")[:150])
        user.save()
        return Response(DoctorDetailSerializer(profile, context={"request": request}).data)


class SlotCreate(APIView):
    permission_classes = [IsApprovedDoctor]

    def post(self, request):
        serializer = SlotCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            slots = create_slots(
                request.user.doctor_profile,
                serializer.validated_data["date"],
                serializer.validated_data["start"],
                serializer.validated_data["end"],
                serializer.validated_data["minutes"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        log_access(request.user, "add_slots", f"{len(slots)} slots", request)
        return Response(SlotSerializer(slots, many=True, context={"request": request}).data, status=201)


class SlotDelete(APIView):
    permission_classes = [IsApprovedDoctor]

    def delete(self, request, pk):
        slot = get_object_or_404(Slot, pk=pk, doctor=request.user.doctor_profile)
        if slot.is_booked:
            return Response({"detail": "A patient already booked this slot."}, status=400)
        slot.delete()
        return Response(status=204)


class AppointmentListCreate(APIView):
    def get(self, request):
        qs = scoped_appointments(request.user)
        if request.user.role == User.Role.ADMIN:
            return Response(AdminAppointmentSerializer(qs.order_by("-created_at")[:200], many=True).data)
        if request.user.role == User.Role.DOCTOR:
            qs = qs.annotate(
                urgent_first=Case(
                    When(is_urgent=True, status=Appointment.Status.CONFIRMED, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by("urgent_first", "slot__date", "slot__start_time")
        return Response(AppointmentSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request):
        if request.user.role != User.Role.PATIENT:
            return Response({"detail": "Only a patient can book a visit."}, status=403)
        serializer = BookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                slot = (
                    Slot.objects.select_for_update()
                    .select_related("doctor", "doctor__user")
                    .get(pk=serializer.validated_data["slot_id"])
                )
                if slot.is_booked:
                    return Response({"detail": "That slot was just taken."}, status=400)
                if not slot.doctor.is_approved or slot.doctor.declined:
                    return Response({"detail": "This doctor is not taking bookings."}, status=400)
                slot_at = timezone.make_aware(
                    datetime.combine(slot.date, slot.start_time),
                    timezone.get_current_timezone(),
                )
                if slot_at <= timezone.localtime():
                    return Response({"detail": "That slot is already in the past."}, status=400)
                slot.is_booked = True
                slot.save(update_fields=["is_booked"])
                appointment = Appointment.objects.create(
                    patient=request.user,
                    doctor=slot.doctor,
                    slot=slot,
                    symptoms=(serializer.validated_data.get("symptoms") or "").strip(),
                    is_urgent=serializer.validated_data.get("is_urgent", False),
                    status=Appointment.Status.CONFIRMED,
                )
        except Slot.DoesNotExist:
            return Response({"detail": "That slot does not exist."}, status=404)
        add_booking_reminders(appointment)
        log_access(
            request.user,
            "book_appointment",
            f"appointment {appointment.id}" + (" urgent" if appointment.is_urgent else ""),
            request,
        )
        appointment = scoped_appointments(request.user).get(pk=appointment.pk)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data, status=201)


class AppointmentDetail(APIView):
    def get(self, request, pk):
        if request.user.role == User.Role.ADMIN:
            return Response({"detail": "Admins do not have access to medical records."}, status=403)
        appointment = get_object_or_404(scoped_appointments(request.user), pk=pk)
        if request.user.role == User.Role.DOCTOR:
            log_access(request.user, "view_record", f"appointment {appointment.id}", request)
        return Response(
            AppointmentSerializer(
                appointment,
                context={"request": request, "include_record": True},
            ).data
        )


class AppointmentAcknowledge(APIView):
    permission_classes = [IsApprovedDoctor]

    def post(self, request, pk):
        appointment = get_object_or_404(scoped_appointments(request.user), pk=pk)
        if appointment.acknowledged_at is None:
            appointment.acknowledged_at = timezone.now()
            appointment.save(update_fields=["acknowledged_at"])
        return Response(
            AppointmentSerializer(
                appointment, context={"request": request, "include_record": True}
            ).data
        )


class AppointmentComplete(APIView):
    permission_classes = [IsApprovedDoctor]

    def post(self, request, pk):
        appointment = get_object_or_404(scoped_appointments(request.user), pk=pk)
        if appointment.status == Appointment.Status.CANCELLED:
            return Response({"detail": "This visit was cancelled."}, status=400)
        medicines = (request.data.get("medicines") or "").strip()
        advice = (request.data.get("advice") or "").strip()
        notes = (request.data.get("clinical_notes") or "").strip()
        if not medicines:
            return Response({"medicines": ["Write the prescription before completing the visit."]}, status=400)
        if len(medicines) > 4000 or len(advice) > 2000 or len(notes) > 4000:
            return Response({"detail": "That note is too long."}, status=400)
        appointment.clinical_notes = notes
        appointment.status = Appointment.Status.COMPLETED
        if appointment.acknowledged_at is None:
            appointment.acknowledged_at = timezone.now()
        appointment.save()
        Prescription.objects.update_or_create(
            appointment=appointment,
            defaults={
                "doctor": appointment.doctor,
                "patient": appointment.patient,
                "medicines": medicines,
                "advice": advice,
            },
        )
        log_access(request.user, "write_prescription", f"appointment {appointment.id}", request)
        appointment = scoped_appointments(request.user).get(pk=appointment.pk)
        return Response(AppointmentSerializer(appointment, context={"request": request, "include_record": True}).data)


class AppointmentCancel(APIView):
    def post(self, request, pk):
        if request.user.role == User.Role.ADMIN:
            return Response({"detail": "Admins do not change medical visits."}, status=403)
        with transaction.atomic():
            appointment = get_object_or_404(scoped_appointments(request.user).select_for_update(), pk=pk)
            if appointment.status == Appointment.Status.COMPLETED:
                return Response({"detail": "A completed visit stays on the record."}, status=400)
            appointment.status = Appointment.Status.CANCELLED
            appointment.save(update_fields=["status", "updated_at"])
            appointment.slot.is_booked = False
            appointment.slot.save(update_fields=["is_booked"])
            Reminder.objects.filter(appointment=appointment).delete()
        log_access(request.user, "cancel_appointment", f"appointment {appointment.id}", request)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)


class AppointmentRate(APIView):
    permission_classes = [IsPatient]

    def post(self, request, pk):
        appointment = get_object_or_404(scoped_appointments(request.user), pk=pk)
        if appointment.status != Appointment.Status.COMPLETED:
            return Response({"detail": "You can rate a visit after it is completed."}, status=400)
        try:
            appointment.rating
            return Response({"detail": "You already rated this visit."}, status=400)
        except Rating.DoesNotExist:
            pass
        try:
            score = int(request.data.get("score"))
        except (TypeError, ValueError):
            return Response({"score": ["Choose a rating from 1 to 5."]}, status=400)
        if score < 1 or score > 5:
            return Response({"score": ["Choose a rating from 1 to 5."]}, status=400)
        Rating.objects.create(
            appointment=appointment,
            patient=request.user,
            doctor=appointment.doctor,
            score=score,
            comment=str(request.data.get("comment") or "")[:300],
        )
        return Response(AppointmentSerializer(scoped_appointments(request.user).get(pk=pk), context={"request": request}).data)


class ReportListCreate(APIView):
    def get(self, request):
        if request.user.role == User.Role.PATIENT:
            qs = request.user.reports.all()
        elif request.user.role == User.Role.DOCTOR:
            patient_id = request.query_params.get("patient")
            if not patient_id:
                return Response({"detail": "Open files from a visit, not as a general list."}, status=400)
            patient = get_object_or_404(User, pk=patient_id, role=User.Role.PATIENT)
            if not doctor_has_patient(request.user.doctor_profile, patient):
                return Response(
                    {"detail": "You can only open files for a patient you have a visit with."},
                    status=403,
                )
            qs = patient.reports.all()
        else:
            return Response({"detail": "Admins do not have access to medical files."}, status=403)
        return Response(ReportSerializer(qs, many=True).data)

    def post(self, request):
        if request.user.role != User.Role.PATIENT:
            return Response({"detail": "Only a patient can add a report to her folder."}, status=403)
        upload = request.FILES.get("file")
        title = (request.data.get("title") or "").strip()
        if not upload or not title:
            return Response({"detail": "Add a title and a file."}, status=400)
        if len(title) > 140:
            return Response({"title": ["Keep the title under 140 characters."]}, status=400)
        appointment = None
        if request.data.get("appointment"):
            appointment = get_object_or_404(
                Appointment, pk=request.data["appointment"], patient=request.user
            )
        raw = upload.read()
        try:
            stored, content_type = store_bytes(raw, upload.name, upload.content_type or "")
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        report = Report.objects.create(
            patient=request.user,
            appointment=appointment,
            title=title,
            original_name=safe_filename(upload.name),
            stored_name=stored,
            content_type=content_type,
            size=len(raw),
        )
        log_access(request.user, "upload_report", f"report {report.id}", request)
        return Response(ReportSerializer(report).data, status=201)


class ReportDownload(APIView):
    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        user = request.user
        allowed = False
        if user.role == User.Role.PATIENT and report.patient_id == user.id:
            allowed = True
        elif user.role == User.Role.DOCTOR:
            try:
                allowed = doctor_has_patient(user.doctor_profile, report.patient)
            except DoctorProfile.DoesNotExist:
                allowed = False
        if not allowed:
            log_access(user, "download_denied", f"report {report.id}", request)
            return Response({"detail": "You cannot open this file."}, status=403)
        data = read_encrypted(report.stored_name)
        log_access(user, "download_report", f"report {report.id}", request)
        response = HttpResponse(data, content_type=report.content_type)
        response["Content-Disposition"] = f'attachment; filename="{safe_filename(report.original_name)}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class PeriodListCreate(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        return Response(PeriodSerializer(request.user.period_logs.all(), many=True).data)

    def post(self, request):
        start = request.data.get("start_date")
        end = request.data.get("end_date") or None
        flow = request.data.get("flow") or PeriodLog.Flow.MEDIUM
        if flow not in PeriodLog.Flow.values:
            return Response({"flow": ["Choose light, medium, or heavy."]}, status=400)
        serializer = PeriodSerializer(
            data={
                "start_date": start,
                "end_date": end,
                "flow": flow,
                "symptoms": str(request.data.get("symptoms") or "")[:300],
                "notes": str(request.data.get("notes") or "")[:1000],
            }
        )
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("end_date") and serializer.validated_data["end_date"] < serializer.validated_data["start_date"]:
            return Response({"end_date": ["The end date cannot be before the start date."]}, status=400)
        log = serializer.save(patient=request.user)
        refresh_period_reminder(request.user)
        return Response(PeriodSerializer(log).data, status=201)


class PeriodDelete(APIView):
    permission_classes = [IsPatient]

    def delete(self, request, pk):
        log = get_object_or_404(PeriodLog, pk=pk, patient=request.user)
        log.delete()
        refresh_period_reminder(request.user)
        return Response(status=204)


class PregnancyView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        active = request.user.pregnancy_logs.filter(is_active=True).first()
        return Response({"active": pregnancy_summary(active)})

    def post(self, request):
        raw = request.data.get("lmp")
        if not raw:
            return Response({"lmp": ["Enter the first day of your last period."]}, status=400)
        try:
            lmp = datetime.strptime(str(raw), "%Y-%m-%d").date()
        except ValueError:
            return Response({"lmp": ["Use a date like 2026-01-15."]}, status=400)
        today = timezone.localdate()
        if lmp > today:
            return Response({"lmp": ["That date is in the future."]}, status=400)
        if lmp < today - timedelta(days=320):
            return Response({"lmp": ["Enter a last-period date from this pregnancy."]}, status=400)
        notes = str(request.data.get("notes") or "")[:1000]
        with transaction.atomic():
            request.user.pregnancy_logs.filter(is_active=True).update(is_active=False)
            log = PregnancyLog.objects.create(patient=request.user, lmp=lmp, notes=notes, is_active=True)
        refresh_pregnancy_reminder(request.user)
        return Response({"active": pregnancy_summary(log)}, status=201)


class PregnancyClose(APIView):
    permission_classes = [IsPatient]

    def post(self, request):
        request.user.pregnancy_logs.filter(is_active=True).update(is_active=False)
        refresh_pregnancy_reminder(request.user)
        return Response({"active": None})


class ReminderList(APIView):
    def get(self, request):
        return Response(ReminderSerializer(request.user.reminders.all(), many=True).data)


class ReminderRead(APIView):
    def post(self, request, pk):
        reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
        reminder.is_read = True
        reminder.save(update_fields=["is_read"])
        return Response(ReminderSerializer(reminder).data)


class ForumPostListCreate(APIView):
    def get(self, request):
        include_removed = request.user.role == User.Role.ADMIN and request.query_params.get("all") == "1"
        qs = ForumPost.objects.select_related("author").annotate(
            visible_comments=Count("comments", filter=Q(comments__is_removed=False))
        )
        if not include_removed:
            qs = qs.filter(is_removed=False)
        return Response(ForumPostSerializer(qs, many=True).data)

    def post(self, request):
        title = (request.data.get("title") or "").strip()
        body = (request.data.get("body") or "").strip()
        if len(title) < 3 or len(body) < 2:
            return Response({"detail": "Add a title and a message."}, status=400)
        if len(title) > 140 or len(body) > 5000:
            return Response({"detail": "That post is too long."}, status=400)
        post = ForumPost.objects.create(author=request.user, title=title, body=body)
        return Response(ForumPostSerializer(post).data, status=201)


class ForumPostDetail(APIView):
    def get(self, request, pk):
        post = get_object_or_404(ForumPost.objects.select_related("author"), pk=pk)
        if post.is_removed and request.user.role != User.Role.ADMIN:
            return Response({"detail": "This post was removed."}, status=404)
        return Response(ForumPostDetailSerializer(post, context={"request": request}).data)


class ForumCommentCreate(APIView):
    def post(self, request, pk):
        post = get_object_or_404(ForumPost, pk=pk, is_removed=False)
        body = (request.data.get("body") or "").strip()
        if len(body) < 1 or len(body) > 2000:
            return Response({"detail": "Write a comment under 2000 characters."}, status=400)
        ForumComment.objects.create(post=post, author=request.user, body=body)
        return Response(ForumPostDetailSerializer(post, context={"request": request}).data, status=201)


class ForumPostModerate(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        post = get_object_or_404(ForumPost, pk=pk)
        action = request.data.get("action")
        if action == "remove":
            post.is_removed = True
            post.removed_reason = str(request.data.get("reason") or "Removed by admin")[:200]
        elif action == "restore":
            post.is_removed = False
            post.removed_reason = ""
        else:
            return Response({"action": ["Use remove or restore."]}, status=400)
        post.save()
        log_access(request.user, "moderate_post", f"post {post.id} {action}", request)
        return Response(ForumPostDetailSerializer(post, context={"request": request}).data)


class ForumCommentModerate(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        comment = get_object_or_404(ForumComment, pk=pk)
        action = request.data.get("action")
        if action == "remove":
            comment.is_removed = True
            comment.removed_reason = str(request.data.get("reason") or "Removed by admin")[:200]
        elif action == "restore":
            comment.is_removed = False
            comment.removed_reason = ""
        else:
            return Response({"action": ["Use remove or restore."]}, status=400)
        comment.save()
        log_access(request.user, "moderate_comment", f"comment {comment.id} {action}", request)
        return Response({"ok": True})


def _article_queryset(user):
    qs = Article.objects.select_related("author__user")
    if user.role == User.Role.ADMIN:
        return qs
    if user.role == User.Role.DOCTOR:
        try:
            return qs.filter(Q(is_published=True) | Q(author=user.doctor_profile))
        except DoctorProfile.DoesNotExist:
            return qs.filter(is_published=True)
    return qs.filter(is_published=True)


class ArticleListCreate(APIView):
    def get(self, request):
        articles = _article_queryset(request.user)
        return Response(ArticleSerializer(articles, many=True).data)

    def post(self, request):
        title = (request.data.get("title") or "").strip()
        summary = (request.data.get("summary") or "").strip()
        body = (request.data.get("body") or "").strip()
        if len(title) < 3 or len(summary) < 3 or len(body) < 10:
            return Response({"detail": "Add a title, a short summary, and the article."}, status=400)
        if len(title) > 160 or len(summary) > 280 or len(body) > 8000:
            return Response({"detail": "That article is too long."}, status=400)
        if request.user.role == User.Role.DOCTOR:
            profile = request.user.doctor_profile
            if not profile.is_approved:
                return Response({"detail": "Approved doctors write the articles."}, status=403)
            author = profile
        elif request.user.role == User.Role.ADMIN:
            author = get_object_or_404(
                DoctorProfile, pk=request.data.get("author_id"), is_approved=True, declined=False
            )
        else:
            return Response({"detail": "Articles come from verified doctor accounts."}, status=403)
        published = request.data.get("is_published", True)
        article = Article.objects.create(
            author=author,
            title=title,
            summary=summary,
            body=body,
            is_published=bool(published) if not isinstance(published, str) else published.lower() != "false",
        )
        log_access(request.user, "write_article", f"article {article.id}", request)
        return Response(ArticleDetailSerializer(article).data, status=201)


class ArticleDetail(APIView):
    def get(self, request, pk):
        article = get_object_or_404(_article_queryset(request.user), pk=pk)
        return Response(ArticleDetailSerializer(article).data)

    def put(self, request, pk):
        article = get_object_or_404(Article.objects.select_related("author__user"), pk=pk)
        is_author = (
            request.user.role == User.Role.DOCTOR
            and getattr(request.user, "doctor_profile", None)
            and request.user.doctor_profile.id == article.author_id
        )
        if request.user.role != User.Role.ADMIN and not is_author:
            return Response({"detail": "You can only edit your own article."}, status=403)
        for field, limit in (("title", 160), ("summary", 280), ("body", 8000)):
            if field in request.data:
                setattr(article, field, str(request.data.get(field) or "")[:limit])
        if "is_published" in request.data:
            value = request.data.get("is_published")
            article.is_published = value if isinstance(value, bool) else str(value).lower() != "false"
        article.save()
        return Response(ArticleDetailSerializer(article).data)


class ComplaintListCreate(APIView):
    def get(self, request):
        if request.user.role == User.Role.ADMIN:
            qs = Complaint.objects.select_related("user")
        else:
            qs = Complaint.objects.filter(user=request.user)
        return Response(ComplaintSerializer(qs, many=True).data)

    def post(self, request):
        subject = (request.data.get("subject") or "").strip()
        body = (request.data.get("body") or "").strip()
        if len(subject) < 3 or len(body) < 3:
            return Response({"detail": "Add a subject and what happened."}, status=400)
        if len(subject) > 140 or len(body) > 4000:
            return Response({"detail": "That complaint is too long."}, status=400)
        complaint = Complaint.objects.create(user=request.user, subject=subject, body=body)
        log_access(request.user, "complaint", f"complaint {complaint.id}", request)
        return Response(ComplaintSerializer(complaint).data, status=201)


class ComplaintResolve(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        complaint.status = Complaint.Status.RESOLVED
        complaint.admin_note = str(request.data.get("admin_note") or "")[:1000]
        complaint.save()
        log_access(request.user, "resolve_complaint", f"complaint {complaint.id}", request)
        return Response(ComplaintSerializer(complaint).data)


class AdminSummary(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        urgent = (
            Appointment.objects.filter(
                is_urgent=True,
                status=Appointment.Status.CONFIRMED,
                acknowledged_at__isnull=True,
            )
            .select_related("slot", "doctor__user", "patient")
            .order_by("created_at")
        )
        return Response(
            {
                "pending_doctors": DoctorProfile.objects.filter(is_approved=False, declined=False).count(),
                "open_complaints": Complaint.objects.filter(status=Complaint.Status.OPEN).count(),
                "urgent_waiting": urgent.count(),
                "forum_posts": ForumPost.objects.filter(is_removed=False).count(),
                "removed_posts": ForumPost.objects.filter(is_removed=True).count(),
                "urgent": AdminAppointmentSerializer(urgent[:8], many=True).data,
            }
        )


class AdminDoctors(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        doctors = DoctorProfile.objects.select_related("user").order_by("is_approved", "user__first_name")
        return Response(
            [
                {
                    "id": doctor.id,
                    "name": doctor.user.get_full_name(),
                    "email": doctor.user.email,
                    "phone": doctor.user.phone,
                    "specialty": doctor.specialty,
                    "qualifications": doctor.qualifications,
                    "clinic_name": doctor.clinic_name,
                    "clinic_address": doctor.clinic_address,
                    "fee": doctor.fee,
                    "experience_years": doctor.experience_years,
                    "is_approved": doctor.is_approved,
                    "declined": doctor.declined,
                }
                for doctor in doctors
            ]
        )


class AdminDoctorApprove(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        doctor = get_object_or_404(DoctorProfile, pk=pk)
        doctor.is_approved = True
        doctor.declined = False
        doctor.save(update_fields=["is_approved", "declined"])
        log_access(request.user, "approve_doctor", f"doctor {doctor.id}", request)
        return Response({"ok": True, "is_approved": True})


class AdminDoctorDecline(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        doctor = get_object_or_404(DoctorProfile, pk=pk)
        doctor.is_approved = False
        doctor.declined = True
        doctor.save(update_fields=["is_approved", "declined"])
        log_access(request.user, "decline_doctor", f"doctor {doctor.id}", request)
        return Response({"ok": True, "declined": True})


class AdminLogs(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        logs = AccessLog.objects.select_related("user")[:200]
        return Response(AccessLogSerializer(logs, many=True).data)


class AdminUrgent(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        urgent = (
            Appointment.objects.filter(is_urgent=True)
            .exclude(status=Appointment.Status.CANCELLED)
            .select_related("slot", "doctor__user", "patient")
            .order_by("acknowledged_at", "created_at")
        )
        return Response(AdminAppointmentSerializer(urgent[:200], many=True).data)
