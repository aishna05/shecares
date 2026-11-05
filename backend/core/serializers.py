from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    Appointment,
    Article,
    Complaint,
    DoctorProfile,
    ForumComment,
    ForumPost,
    PatientProfile,
    PeriodLog,
    Prescription,
    Rating,
    Reminder,
    Report,
    Slot,
    User,
)
from .services import pregnancy_summary, public_author


class UserSerializer(serializers.ModelSerializer):
    is_approved = serializers.SerializerMethodField()
    declined = serializers.SerializerMethodField()
    specialty = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    cycle_length = serializers.SerializerMethodField()
    period_length = serializers.SerializerMethodField()
    today = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "forum_name",
            "is_approved",
            "declined",
            "specialty",
            "city",
            "cycle_length",
            "period_length",
            "today",
        ]

    def _doctor(self, obj):
        if obj.role != User.Role.DOCTOR:
            return None
        try:
            return obj.doctor_profile
        except DoctorProfile.DoesNotExist:
            return None

    def _patient(self, obj):
        if obj.role != User.Role.PATIENT:
            return None
        try:
            return obj.patient_profile
        except PatientProfile.DoesNotExist:
            return None

    def get_is_approved(self, obj):
        doctor = self._doctor(obj)
        if doctor is None:
            return None
        return doctor.is_approved

    def get_declined(self, obj):
        doctor = self._doctor(obj)
        return bool(doctor and doctor.declined)

    def get_specialty(self, obj):
        doctor = self._doctor(obj)
        return doctor.specialty if doctor else None

    def get_city(self, obj):
        patient = self._patient(obj)
        return patient.city if patient else None

    def get_cycle_length(self, obj):
        patient = self._patient(obj)
        return patient.cycle_length if patient else None

    def get_period_length(self, obj):
        patient = self._patient(obj)
        return patient.period_length if patient else None

    def get_today(self, obj):
        return timezone.localdate().isoformat()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        if attrs.get(self.username_field):
            attrs[self.username_field] = attrs[self.username_field].strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False)
    role = serializers.ChoiceField(choices=[User.Role.PATIENT, User.Role.DOCTOR])
    forum_name = serializers.CharField(max_length=40, allow_blank=True, required=False)
    city = serializers.CharField(max_length=80, allow_blank=True, required=False)
    specialty = serializers.CharField(max_length=80, allow_blank=True, required=False)
    qualifications = serializers.CharField(max_length=200, allow_blank=True, required=False)
    clinic_name = serializers.CharField(max_length=160, allow_blank=True, required=False)
    clinic_address = serializers.CharField(max_length=240, allow_blank=True, required=False)
    fee = serializers.IntegerField(required=False, min_value=0, max_value=20000)
    experience_years = serializers.IntegerField(required=False, min_value=0, max_value=80)
    treats = serializers.CharField(max_length=300, allow_blank=True, required=False)
    bio = serializers.CharField(allow_blank=True, required=False)

    def validate_email(self, value):
        value = value.strip().lower()
        if len(value) > 150:
            raise serializers.ValidationError("Use an email shorter than 150 characters.")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        if data["role"] == User.Role.DOCTOR:
            missing = {}
            for field in ("specialty", "qualifications", "clinic_name"):
                if not (data.get(field) or "").strip():
                    missing[field] = "This field is required for a gynecologist."
            if missing:
                raise serializers.ValidationError(missing)
        return data

    def create(self, data):
        with transaction.atomic():
            user = User.objects.create_user(
                data["email"],
                data["email"],
                data["password"],
                first_name=data["first_name"].strip(),
                last_name=(data.get("last_name") or "").strip(),
                phone=(data.get("phone") or "").strip(),
                role=data["role"],
                forum_name=(data.get("forum_name") or data["first_name"]).strip()[:40],
            )
            if data["role"] == User.Role.PATIENT:
                PatientProfile.objects.create(user=user, city=(data.get("city") or "").strip())
            else:
                DoctorProfile.objects.create(
                    user=user,
                    specialty=data["specialty"].strip(),
                    qualifications=data["qualifications"].strip(),
                    clinic_name=data["clinic_name"].strip(),
                    clinic_address=(data.get("clinic_address") or "").strip(),
                    fee=data.get("fee") or 0,
                    experience_years=data.get("experience_years") or 0,
                    treats=(data.get("treats") or "").strip(),
                    bio=(data.get("bio") or "").strip(),
                    is_approved=False,
                )
        return user


class SlotSerializer(serializers.ModelSerializer):
    booked_by = serializers.SerializerMethodField()

    class Meta:
        model = Slot
        fields = ["id", "date", "start_time", "end_time", "is_booked", "booked_by"]

    def get_booked_by(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not obj.is_booked or not user or user.role != User.Role.DOCTOR:
            return None
        try:
            if user.doctor_profile.id != obj.doctor_id:
                return None
        except DoctorProfile.DoesNotExist:
            return None
        try:
            appointment = obj.appointment
        except Appointment.DoesNotExist:
            return None
        if appointment.status == Appointment.Status.CANCELLED:
            return None
        return appointment.patient.get_full_name()


class DoctorCardSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    rating_avg = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    open_slots = serializers.SerializerMethodField()
    next_slot = serializers.SerializerMethodField()
    treats = serializers.SerializerMethodField()
    reasons = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "name",
            "specialty",
            "qualifications",
            "bio",
            "clinic_name",
            "clinic_address",
            "fee",
            "experience_years",
            "treats",
            "rating_avg",
            "rating_count",
            "open_slots",
            "next_slot",
            "reasons",
        ]

    def get_name(self, obj):
        return obj.user.get_full_name()

    def get_rating_avg(self, obj):
        value = getattr(obj, "rating_avg", None)
        if value is None:
            return None
        return round(float(value), 1)

    def get_rating_count(self, obj):
        return getattr(obj, "rating_count", 0) or 0

    def get_open_slots(self, obj):
        if hasattr(obj, "open_slot_count"):
            return obj.open_slot_count
        return obj.slots.filter(is_booked=False, date__gte=timezone.localdate()).count()

    def get_next_slot(self, obj):
        slot = (
            obj.slots.filter(is_booked=False, date__gte=timezone.localdate())
            .order_by("date", "start_time")
            .first()
        )
        if not slot:
            return None
        return {"id": slot.id, "date": slot.date, "start_time": slot.start_time, "end_time": slot.end_time}

    def get_treats(self, obj):
        return [part.strip() for part in obj.treats.split(",") if part.strip()]

    def get_reasons(self, obj):
        return self.context.get("reasons", {}).get(obj.id, [])


class DoctorDetailSerializer(DoctorCardSerializer):
    slots = serializers.SerializerMethodField()
    is_approved = serializers.BooleanField(read_only=True)
    declined = serializers.BooleanField(read_only=True)

    class Meta(DoctorCardSerializer.Meta):
        fields = DoctorCardSerializer.Meta.fields + ["slots", "is_approved", "declined"]

    def get_slots(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        mine = False
        if user and user.role == User.Role.DOCTOR:
            try:
                mine = user.doctor_profile.id == obj.id
            except DoctorProfile.DoesNotExist:
                mine = False
        qs = obj.slots.all().order_by("date", "start_time")
        if mine:
            qs = qs.filter(date__gte=timezone.localdate() - timedelta(days=1))
            qs = qs.prefetch_related("appointment__patient")
        else:
            qs = qs.filter(is_booked=False, date__gte=timezone.localdate())
        return SlotSerializer(qs, many=True, context=self.context).data


class PrescriptionSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = ["id", "medicines", "advice", "created_at", "doctor_name"]

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name()


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "title", "original_name", "content_type", "size", "uploaded_at", "appointment"]


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodLog
        fields = ["id", "start_date", "end_date", "flow", "symptoms", "notes", "created_at"]


class AppointmentSerializer(serializers.ModelSerializer):
    slot = SlotSerializer()
    doctor = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    prescription = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    record = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "status",
            "is_urgent",
            "symptoms",
            "clinical_notes",
            "created_at",
            "acknowledged_at",
            "slot",
            "doctor",
            "patient",
            "prescription",
            "rating",
            "record",
        ]

    def get_doctor(self, obj):
        return {
            "id": obj.doctor_id,
            "name": obj.doctor.user.get_full_name(),
            "specialty": obj.doctor.specialty,
            "clinic_name": obj.doctor.clinic_name,
        }

    def get_patient(self, obj):
        return {"id": obj.patient_id, "name": obj.patient.get_full_name()}

    def get_prescription(self, obj):
        try:
            return PrescriptionSerializer(obj.prescription).data
        except Prescription.DoesNotExist:
            return None

    def get_rating(self, obj):
        try:
            return {"score": obj.rating.score, "comment": obj.rating.comment}
        except Rating.DoesNotExist:
            return None

    def get_record(self, obj):
        request = self.context.get("request")
        if not self.context.get("include_record"):
            return None
        user = getattr(request, "user", None)
        if not user or user.role != User.Role.DOCTOR:
            return None
        patient = obj.patient
        active = patient.pregnancy_logs.filter(is_active=True).first()
        prescriptions = (
            patient.prescriptions.select_related("doctor__user").order_by("-created_at")[:20]
        )
        return {
            "reports": ReportSerializer(patient.reports.all()[:30], many=True).data,
            "periods": PeriodSerializer(patient.period_logs.all()[:12], many=True).data,
            "pregnancy": pregnancy_summary(active),
            "prescriptions": PrescriptionSerializer(prescriptions, many=True).data,
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("record") is None:
            data.pop("record", None)
        return data


class AdminAppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    when = serializers.SerializerMethodField()
    waiting_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "status",
            "is_urgent",
            "created_at",
            "acknowledged_at",
            "doctor_name",
            "patient_name",
            "when",
            "waiting_minutes",
        ]

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name()

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_when(self, obj):
        return {"date": obj.slot.date, "start_time": obj.slot.start_time, "end_time": obj.slot.end_time}

    def get_waiting_minutes(self, obj):
        if obj.acknowledged_at or not obj.is_urgent or obj.status != Appointment.Status.CONFIRMED:
            return None
        return int((timezone.now() - obj.created_at).total_seconds() // 60)


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ["id", "kind", "message", "due_on", "is_read", "created_at", "appointment"]


class ArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_specialty = serializers.CharField(source="author.specialty", read_only=True)
    author_id = serializers.IntegerField(source="author.id", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "summary",
            "is_published",
            "created_at",
            "author_name",
            "author_specialty",
            "author_id",
        ]

    def get_author_name(self, obj):
        return f"Dr. {obj.author.user.get_full_name()}"


class ArticleDetailSerializer(ArticleSerializer):
    class Meta(ArticleSerializer.Meta):
        fields = ArticleSerializer.Meta.fields + ["body"]


class ForumCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = ForumComment
        fields = ["id", "body", "created_at", "is_removed", "author"]

    def get_author(self, obj):
        return public_author(obj.author)


class ForumPostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = ForumPost
        fields = [
            "id",
            "title",
            "body",
            "created_at",
            "is_removed",
            "removed_reason",
            "author",
            "comment_count",
        ]

    def get_author(self, obj):
        return public_author(obj.author)

    def get_comment_count(self, obj):
        if hasattr(obj, "visible_comments"):
            return obj.visible_comments
        return obj.comments.filter(is_removed=False).count()


class ForumPostDetailSerializer(ForumPostSerializer):
    comments = serializers.SerializerMethodField()

    class Meta(ForumPostSerializer.Meta):
        fields = ForumPostSerializer.Meta.fields + ["comments"]

    def get_comments(self, obj):
        request = self.context.get("request")
        qs = obj.comments.select_related("author")
        user = getattr(request, "user", None)
        if not user or user.role != User.Role.ADMIN:
            qs = qs.filter(is_removed=False)
        return ForumCommentSerializer(qs, many=True).data


class ComplaintSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = Complaint
        fields = ["id", "subject", "body", "status", "admin_note", "created_at", "user_name", "user_role"]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.forum_name or "Member"


class AccessLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:
        from .models import AccessLog

        model = AccessLog
        fields = ["id", "action", "detail", "ip", "created_at", "user_name", "user_role"]

    def get_user_name(self, obj):
        if not obj.user:
            return "Removed account"
        return obj.user.get_full_name() or obj.user.email

    def get_user_role(self, obj):
        return obj.user.role if obj.user else ""


class BookSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField()
    symptoms = serializers.CharField(allow_blank=True, required=False, max_length=2000)
    is_urgent = serializers.BooleanField(required=False, default=False)


class SlotCreateSerializer(serializers.Serializer):
    date = serializers.DateField()
    start = serializers.TimeField(input_formats=["%H:%M", "%H:%M:%S"])
    end = serializers.TimeField(input_formats=["%H:%M", "%H:%M:%S"])
    minutes = serializers.IntegerField(min_value=10, max_value=180, default=20)
