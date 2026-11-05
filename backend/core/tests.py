import tempfile
from datetime import time, timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from core.encryption import read_encrypted, store_bytes
from core.models import AccessLog, Appointment, DoctorProfile, PatientProfile, Report, Slot, User

PASSWORD = "SheCares#2026"
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
    "0000000c4944415408d763f8cfff3f0005fe02fe0a3b2c8a0000000049454e44ae426082"
)


def make_user(email, role, first):
    return User.objects.create_user(
        email, email, PASSWORD, role=role, first_name=first, last_name="User"
    )


class PrivacyTests(APITestCase):
    def setUp(self):
        self._media = tempfile.TemporaryDirectory()
        self._override = override_settings(PRIVATE_MEDIA_ROOT=Path(self._media.name))
        self._override.enable()
        self.patient_a = make_user("a@shecares.local", User.Role.PATIENT, "Aisha")
        self.patient_b = make_user("b@shecares.local", User.Role.PATIENT, "Priya")
        PatientProfile.objects.create(user=self.patient_a)
        PatientProfile.objects.create(user=self.patient_b)
        self.doctor_user = make_user("doc@shecares.local", User.Role.DOCTOR, "Meera")
        self.other_user = make_user("other@shecares.local", User.Role.DOCTOR, "Kavita")
        self.pending_user = make_user("wait@shecares.local", User.Role.DOCTOR, "Neha")
        self.admin = make_user("admin@shecares.local", User.Role.ADMIN, "Admin")
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialty="Menstrual health",
            qualifications="MBBS",
            clinic_name="Cycle Clinic",
            treats="period, cramps, pcos",
            is_approved=True,
        )
        self.other = DoctorProfile.objects.create(
            user=self.other_user,
            specialty="Fertility",
            qualifications="MBBS",
            clinic_name="Fertility Room",
            treats="fertility",
            is_approved=True,
        )
        DoctorProfile.objects.create(
            user=self.pending_user,
            specialty="General gynecology",
            qualifications="MBBS",
            clinic_name="Waiting Clinic",
            is_approved=False,
        )
        day = timezone.localdate() + timedelta(days=2)
        self.slot = Slot.objects.create(
            doctor=self.doctor, date=day, start_time=time(10, 0), end_time=time(10, 20)
        )
        taken = Slot.objects.create(
            doctor=self.doctor, date=day, start_time=time(11, 0), end_time=time(11, 20), is_booked=True
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient_a,
            doctor=self.doctor,
            slot=taken,
            symptoms="secret-symptom-phrase",
            is_urgent=True,
        )
        stored, content_type = store_bytes(b"secret-report-phrase", "note.png", "image/png")
        self.report_b = Report.objects.create(
            patient=self.patient_b,
            title="Private scan",
            original_name="note.png",
            stored_name=stored,
            content_type=content_type,
            size=len(b"secret-report-phrase"),
        )

    def tearDown(self):
        self._override.disable()
        self._media.cleanup()

    def test_file_on_disk_is_not_plaintext(self):
        raw = (Path(settings.PRIVATE_MEDIA_ROOT) / self.report_b.stored_name).read_bytes()
        self.assertNotIn(b"secret-report-phrase", raw)
        self.assertEqual(read_encrypted(self.report_b.stored_name), b"secret-report-phrase")

    def test_other_patient_doctor_and_admin_cannot_download(self):
        url = f"/api/reports/{self.report_b.id}/download/"
        self.client.force_authenticate(self.patient_a)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.doctor_user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_treating_doctor_can_download_and_outsider_cannot_open_visit(self):
        owned = Slot.objects.create(
            doctor=self.doctor,
            date=timezone.localdate() + timedelta(days=3),
            start_time=time(12, 0),
            end_time=time(12, 20),
            is_booked=True,
        )
        Appointment.objects.create(patient=self.patient_b, doctor=self.doctor, slot=owned, symptoms="scan follow up")
        self.client.force_authenticate(self.doctor_user)
        response = self.client.get(f"/api/reports/{self.report_b.id}/download/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"secret-report-phrase")
        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.client.get(f"/api/reports/{self.report_b.id}/download/").status_code, 403)
        self.client.force_authenticate(self.patient_b)
        hidden = self.client.get(f"/api/appointments/{self.appointment.id}/")
        self.assertEqual(hidden.status_code, 404)

    def test_admin_list_hides_symptoms_and_logs_skip_them(self):
        self.client.force_authenticate(self.patient_a)
        response = self.client.get("/api/appointments/")
        self.assertContains(response, "secret-symptom-phrase")
        self.client.force_authenticate(self.admin)
        admin_list = self.client.get("/api/appointments/")
        self.assertEqual(admin_list.status_code, 200)
        self.assertNotContains(admin_list, "secret-symptom-phrase")
        detail = self.client.get(f"/api/appointments/{self.appointment.id}/")
        self.assertEqual(detail.status_code, 403)
        blob = " ".join(AccessLog.objects.values_list("detail", flat=True))
        self.assertNotIn("secret-symptom-phrase", blob)

    def test_suggestion_does_not_diagnose_and_skips_unapproved_doctors(self):
        self.client.force_authenticate(self.patient_a)
        response = self.client.post("/api/doctors/suggest/", {"symptoms": "irregular periods and cramps"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("does not diagnose", response.data["disclaimer"].lower())
        names = [doctor["name"] for doctor in response.data["doctors"]]
        self.assertIn("Meera User", names)
        self.assertNotIn("Neha User", names)
        listing = self.client.get("/api/doctors/")
        self.assertNotIn("Neha User", [doctor["name"] for doctor in listing.data["doctors"]])

    def test_signup_cannot_create_an_admin(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "new@shecares.local",
                "password": PASSWORD,
                "first_name": "New",
                "role": "admin",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patient_can_book_and_upload_round_trip(self):
        self.client.force_authenticate(self.patient_a)
        booked = self.client.post(
            "/api/appointments/",
            {"slot_id": self.slot.id, "symptoms": "cycle question", "is_urgent": True},
            format="json",
        )
        self.assertEqual(booked.status_code, 201)
        self.assertTrue(booked.data["is_urgent"])
        upload = self.client.post(
            "/api/reports/",
            {"title": "Blood count", "file": SimpleUploadedFile("count.png", PNG, content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201)
        download = self.client.get(f"/api/reports/{upload.data['id']}/download/")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, PNG)
