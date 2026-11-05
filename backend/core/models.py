from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = "patient", "Patient"
        DOCTOR = "doctor", "Gynecologist"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=20, blank=True)
    forum_name = models.CharField(max_length=40, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)


class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")
    city = models.CharField(max_length=80, blank=True)
    cycle_length = models.PositiveSmallIntegerField(default=28)
    period_length = models.PositiveSmallIntegerField(default=5)


class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="doctor_profile")
    specialty = models.CharField(max_length=80)
    qualifications = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    clinic_name = models.CharField(max_length=160)
    clinic_address = models.CharField(max_length=240, blank=True)
    fee = models.PositiveIntegerField(default=0)
    experience_years = models.PositiveSmallIntegerField(default=0)
    treats = models.CharField(max_length=300, blank=True)
    is_approved = models.BooleanField(default=False)
    declined = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_full_name() or self.user.email


class Slot(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="slots")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ["date", "start_time"]
        indexes = [models.Index(fields=["date", "is_booked"])]


class Appointment(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="appointments")
    slot = models.OneToOneField(Slot, on_delete=models.CASCADE, related_name="appointment")
    symptoms = models.TextField(blank=True)
    is_urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    clinical_notes = models.TextField(blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slot__date", "slot__start_time"]


class Prescription(models.Model):
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="prescription"
    )
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="prescriptions")
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescriptions")
    medicines = models.TextField()
    advice = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Report(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    appointment = models.ForeignKey(
        Appointment, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports"
    )
    title = models.CharField(max_length=140)
    original_name = models.CharField(max_length=200)
    stored_name = models.CharField(max_length=80)
    content_type = models.CharField(max_length=80)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]


class PeriodLog(models.Model):
    class Flow(models.TextChoices):
        LIGHT = "light", "Light"
        MEDIUM = "medium", "Medium"
        HEAVY = "heavy", "Heavy"

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="period_logs")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    flow = models.CharField(max_length=10, choices=Flow.choices, default=Flow.MEDIUM)
    symptoms = models.CharField(max_length=300, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]


class PregnancyLog(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pregnancy_logs")
    lmp = models.DateField()
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Reminder(models.Model):
    class Kind(models.TextChoices):
        PERIOD = "period", "Period"
        PREGNANCY = "pregnancy", "Pregnancy"
        APPOINTMENT = "appointment", "Appointment"
        URGENT = "urgent", "Urgent"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reminders")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    appointment = models.ForeignKey(
        Appointment, null=True, blank=True, on_delete=models.CASCADE, related_name="reminders"
    )
    message = models.CharField(max_length=300)
    due_on = models.DateField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_read", "due_on"]


class Article(models.Model):
    author = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="articles")
    title = models.CharField(max_length=160)
    summary = models.CharField(max_length=280)
    body = models.TextField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ForumPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_posts")
    title = models.CharField(max_length=140)
    body = models.TextField()
    is_removed = models.BooleanField(default=False)
    removed_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ForumComment(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_comments")
    body = models.TextField()
    is_removed = models.BooleanField(default=False)
    removed_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Complaint(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaints")
    subject = models.CharField(max_length=140)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AccessLog(models.Model):
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="access_logs"
    )
    action = models.CharField(max_length=40)
    detail = models.CharField(max_length=240, blank=True)
    ip = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Rating(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="rating")
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings_given")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="ratings")
    score = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
