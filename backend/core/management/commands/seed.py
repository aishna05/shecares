from datetime import datetime, time, timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw

from core.encryption import store_bytes
from core.models import (
    AccessLog,
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
    Report,
    Slot,
    User,
)
from core.services import add_booking_reminders, log_access, refresh_period_reminder

PASSWORD = "SheCares#2026"
TIMES = [
    (time(10, 0), time(10, 20)),
    (time(10, 30), time(10, 50)),
    (time(11, 30), time(11, 50)),
    (time(15, 0), time(15, 20)),
    (time(16, 30), time(16, 50)),
]


def make_png(lines):
    image = Image.new("RGB", (960, 280), "#fffaf3")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 960, 10), fill="#7a2e45")
    y = 36
    for line in lines:
        draw.text((32, y), line, fill="#221b16")
        y += 34
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Reset demo data for SheCares. This deletes existing accounts and records."

    def handle(self, *args, **options):
        media = Path(settings.PRIVATE_MEDIA_ROOT)
        if media.exists():
            for item in media.iterdir():
                if item.is_file():
                    item.unlink()
        User.objects.all().delete()
        AccessLog.objects.all().delete()
        Slot.objects.all().delete()

        admin = self._user("admin@shecares.local", "SheCares", "Admin", User.Role.ADMIN)
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        doctors = {
            "meera": self._doctor(
                "meera@shecares.local",
                "Meera",
                "Iyer",
                "General gynecology",
                "MBBS, MS (OBG)",
                "Halasuru Women's Clinic",
                "14 Halasuru Road, Bengaluru",
                700,
                14,
                "discharge, pelvic pain, contraception, checkup, infection",
                "General gynecologist. Clinic visits for infections, contraception, and routine checks.",
            ),
            "ananya": self._doctor(
                "ananya@shecares.local",
                "Ananya",
                "Shah",
                "Obstetrics",
                "MBBS, MD (OBG)",
                "Sabarmati Maternity Centre",
                "22 Riverfront Road, Ahmedabad",
                900,
                11,
                "pregnancy, prenatal, trimester, antenatal",
                "Obstetrician for prenatal clinic visits. She does not replace an emergency ward.",
            ),
            "kavita": self._doctor(
                "kavita@shecares.local",
                "Kavita",
                "Menon",
                "Fertility",
                "MBBS, DNB (OBG)",
                "Marine Lines Fertility Room",
                "8 Marine Lines, Mumbai",
                1500,
                16,
                "fertility, conceive, ivf, ovulation",
                "Fertility consults for people trying to conceive. Suggestions on the site are not a diagnosis.",
            ),
            "riya": self._doctor(
                "riya@shecares.local",
                "Riya",
                "Banerjee",
                "Menstrual health",
                "MBBS, MS (OBG)",
                "Ballygunge Cycle Clinic",
                "5 Gariahat Road, Kolkata",
                800,
                9,
                "period, pcos, irregular, cramps, cycle",
                "Clinic care for irregular cycles, PCOS, and painful periods.",
            ),
            "farah": self._doctor(
                "farah@shecares.local",
                "Farah",
                "Qureshi",
                "Menopause",
                "MBBS, MRCOG",
                "Banjara Women's Clinic",
                "19 Road No. 12, Hyderabad",
                750,
                18,
                "menopause, hot flush, perimenopause",
                "Visits for perimenopause and menopause symptoms.",
            ),
        }
        for profile in doctors.values():
            self._open_slots(profile)

        pending = self._doctor(
            "neha@shecares.local",
            "Neha",
            "Kulkarni",
            "General gynecology",
            "MBBS, DGO",
            "Deccan Clinic",
            "3 FC Road, Pune",
            600,
            6,
            "checkup, contraception",
            "Waiting for an admin to approve this account.",
            approved=False,
        )

        aisha = self._patient("aisha@shecares.local", "Aisha", "Kapoor", "Pune", "Aisha")
        priya = self._patient("priya@shecares.local", "Priya", "Nair", "Kochi", "Priya")

        today = timezone.localdate()
        meera = doctors["meera"]
        ananya = doctors["ananya"]
        kavita = doctors["kavita"]
        riya = doctors["riya"]

        past = self._book(
            aisha,
            meera,
            today - timedelta(days=1),
            time(10, 0),
            time(10, 20),
            "Heavy cramps for two cycles.",
            urgent=False,
            status=Appointment.Status.COMPLETED,
        )
        past.acknowledged_at = timezone.now() - timedelta(days=1)
        past.clinical_notes = "Discussed heavy cramps. No emergency signs described in this visit."
        past.save()
        Prescription.objects.create(
            appointment=past,
            doctor=meera,
            patient=aisha,
            medicines="Tab. Tranexamic acid 500 mg — one tablet three times a day for 3 days.\nTab. Mefenamic acid 250 mg — one tablet when cramps start, up to three times a day.",
            advice="Demo prescription from the last clinic visit. Come back if a pad soaks through in under an hour — that belongs in a hospital, not on this website.",
        )
        Rating.objects.create(appointment=past, patient=aisha, doctor=meera, score=5, comment="She had my old report open.")

        priya_past = self._book(
            priya,
            kavita,
            today - timedelta(days=1),
            time(11, 30),
            time(11, 50),
            "Trying to conceive for eight months.",
            urgent=False,
            status=Appointment.Status.COMPLETED,
        )
        priya_past.acknowledged_at = timezone.now() - timedelta(days=1)
        priya_past.clinical_notes = "Fertility history noted. Follicular scan saved to her folder."
        priya_past.save()
        Prescription.objects.create(
            appointment=priya_past,
            doctor=kavita,
            patient=priya,
            medicines="Folic acid 5 mg — one tablet daily.",
            advice="Demo note. This is not a treatment plan for anyone reading the code.",
        )
        Rating.objects.create(appointment=priya_past, patient=priya, doctor=kavita, score=4, comment="Clear about next steps.")

        urgent = self._book(
            aisha,
            ananya,
            today,
            time(15, 0),
            time(15, 20),
            "One-sided pain and I might be pregnant.",
            urgent=True,
        )
        Appointment.objects.filter(pk=urgent.pk).update(created_at=timezone.now() - timedelta(hours=3))
        add_booking_reminders(urgent)
        log_access(aisha, "book_appointment", f"appointment {urgent.id} urgent")

        follow_up = self._book(
            priya,
            meera,
            today,
            time(11, 30),
            time(11, 50),
            "Follow-up for cycle notes.",
            urgent=False,
        )
        add_booking_reminders(follow_up)

        upcoming = self._book(
            aisha,
            riya,
            today + timedelta(days=3),
            time(10, 30),
            time(10, 50),
            "Irregular cycle, want to show my dates.",
            urgent=False,
        )
        add_booking_reminders(upcoming)

        start = today - timedelta(days=20)
        PeriodLog.objects.create(
            patient=aisha,
            start_date=start,
            end_date=start + timedelta(days=4),
            flow=PeriodLog.Flow.HEAVY,
            symptoms="cramps",
            notes="Logged before the last visit.",
        )
        refresh_period_reminder(aisha)

        self._report(
            aisha,
            past,
            "Haemoglobin report",
            ["SheCares demo lab report", "Patient folder: Aisha Kapoor", "Haemoglobin 12.4 g/dL", "Sample file, not a real result."],
        )
        self._report(
            priya,
            priya_past,
            "Follicular scan",
            ["SheCares demo scan", "Patient folder: Priya Nair", "Sample image so the privacy check has a second file."],
        )

        post = ForumPost.objects.create(
            author=aisha,
            title="How do you keep cycle notes for a visit?",
            body="I used to keep dates in a different app and the doctor never saw them. Is the tracker on here enough to bring to a clinic visit?",
        )
        ForumComment.objects.create(
            post=post,
            author=meera.user,
            body="Bring the dates, not a diagnosis from the internet. The cycle log is enough for me to see the last few periods. This forum is not a consult.",
        )
        ForumPost.objects.create(
            author=priya,
            title="Cheap hormone pills, message me",
            body="Buy hormone kits cheap. Message me on WhatsApp for a discount. Not a doctor.",
        )

        Article.objects.create(
            author=meera,
            title="What to carry to a gynecology visit",
            summary="A short list so the clinic visit is about you, not about searching your phone.",
            body=(
                "Write down the first day of your last two or three periods, any medicines you already take, "
                "and the questions you actually want answered.\n\n"
                "Upload reports to your SheCares folder before the visit so the doctor you booked can open them. "
                "Other doctors on the site cannot.\n\n"
                "This note is general preparation. It does not diagnose a symptom or replace the visit."
            ),
        )
        Article.objects.create(
            author=ananya,
            title="Urgent on this site is not an emergency ward",
            summary="The urgent mark moves a clinic request up the list. It does not send an ambulance.",
            body=(
                "Mark a booking urgent when you need the doctor to see the request first: pain that worries you, "
                "bleeding that is new, or a pregnancy question that should not wait for the next free week.\n\n"
                "If you are fainting, soaking a pad in under an hour, struggling to breathe, or pregnant with severe pain, "
                "go to a hospital. SheCares does not diagnose illness and it is not an emergency service.\n\n"
                "Admin staff can see that an urgent request is waiting. They cannot open your notes or your files."
            ),
        )

        Complaint.objects.create(
            user=aisha,
            subject="No Sunday slot",
            body="I looked for a Sunday clinic visit and could not find one. Can the schedule show weekends when a doctor adds them?",
        )
        AccessLog.objects.create(user=admin, action="login", detail="signed in", ip="127.0.0.1")
        AccessLog.objects.create(user=aisha, action="login", detail="signed in", ip="127.0.0.1")

        self.stdout.write(self.style.SUCCESS("Demo data is ready. Password for every demo account: " + PASSWORD))
        for email, who in (
            ("aisha@shecares.local", "patient"),
            ("priya@shecares.local", "patient"),
            ("meera@shecares.local", "doctor"),
            ("ananya@shecares.local", "doctor with the urgent visit"),
            ("neha@shecares.local", "doctor waiting for approval"),
            ("admin@shecares.local", "admin"),
        ):
            self.stdout.write(f"  {email}  {who}")
        self.stdout.write(f"Pending doctor id: {pending.id}")

    def _user(self, email, first, last, role, forum_name=""):
        return User.objects.create_user(
            email,
            email,
            PASSWORD,
            first_name=first,
            last_name=last,
            role=role,
            forum_name=forum_name or first,
        )

    def _patient(self, email, first, last, city, forum_name):
        user = self._user(email, first, last, User.Role.PATIENT, forum_name)
        PatientProfile.objects.create(user=user, city=city, cycle_length=28, period_length=5)
        return user

    def _doctor(self, email, first, last, specialty, qualifications, clinic, address, fee, years, treats, bio, approved=True):
        user = self._user(email, first, last, User.Role.DOCTOR)
        return DoctorProfile.objects.create(
            user=user,
            specialty=specialty,
            qualifications=qualifications,
            bio=bio,
            clinic_name=clinic,
            clinic_address=address,
            fee=fee,
            experience_years=years,
            treats=treats,
            is_approved=approved,
        )

    def _open_slots(self, doctor):
        now = timezone.localtime()
        zone = timezone.get_current_timezone()
        for offset in range(0, 6):
            day = now.date() + timedelta(days=offset)
            for start, end in TIMES:
                start_at = timezone.make_aware(datetime.combine(day, start), zone)
                if start_at <= now:
                    continue
                Slot.objects.create(doctor=doctor, date=day, start_time=start, end_time=end)

    def _book(self, patient, doctor, day, start, end, symptoms, urgent, status=Appointment.Status.CONFIRMED):
        slot = Slot.objects.filter(doctor=doctor, date=day, start_time=start).first()
        if slot is None:
            slot = Slot.objects.create(
                doctor=doctor, date=day, start_time=start, end_time=end, is_booked=True
            )
        else:
            slot.is_booked = True
            slot.save(update_fields=["is_booked"])
        return Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            slot=slot,
            symptoms=symptoms,
            is_urgent=urgent,
            status=status,
        )

    def _report(self, patient, appointment, title, lines):
        data = make_png(lines)
        stored, content_type = store_bytes(data, "report.png", "image/png")
        Report.objects.create(
            patient=patient,
            appointment=appointment,
            title=title,
            original_name="report.png",
            stored_name=stored,
            content_type=content_type,
            size=len(data),
        )
