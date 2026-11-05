import re
from datetime import datetime, timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone

from .models import Appointment, DoctorProfile, Reminder, Slot, User

SUGGEST_DISCLAIMER = (
    "This matches the words you typed to specialties the gynecologists say they treat. "
    "SheCares does not diagnose illness. If you are seriously unwell, go to a hospital."
)

SPECIALTY_KEYWORDS = [
    (
        "Obstetrics",
        ["pregnant", "pregnancy", "prenatal", "antenatal", "trimester", "labour", "labor", "miscarriage"],
    ),
    (
        "Fertility",
        ["fertility", "conceive", "infertility", "ivf", "trying to conceive", "ovulation"],
    ),
    (
        "Menopause",
        ["menopause", "hot flush", "hot flash", "perimenopause", "night sweat"],
    ),
    (
        "Menstrual health",
        ["period", "periods", "cycle", "pcos", "pcod", "irregular", "cramp", "cramps", "spotting", "bleeding"],
    ),
    (
        "General gynecology",
        ["discharge", "infection", "itch", "itching", "pelvic", "contraception", "checkup", "check-up"],
    ),
]


def client_ip(request):
    if request is None:
        return ""
    return (request.META.get("REMOTE_ADDR") or "")[:64]


def log_access(user, action, detail="", request=None):
    from .models import AccessLog

    AccessLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        detail=(detail or "")[:240],
        ip=client_ip(request),
    )


def public_author(user):
    if user is None:
        return {"name": "Member", "role": "patient", "verified": False}
    if user.role == User.Role.DOCTOR:
        profile = getattr(user, "doctor_profile", None)
        verified = bool(profile and profile.is_approved)
        return {"name": f"Dr. {user.get_full_name()}", "role": "doctor", "verified": verified}
    if user.role == User.Role.ADMIN:
        return {"name": "SheCares admin", "role": "admin", "verified": False}
    return {"name": user.forum_name or user.first_name or "Member", "role": "patient", "verified": False}


def doctor_has_patient(doctor_profile, patient):
    return (
        Appointment.objects.filter(doctor=doctor_profile, patient=patient)
        .exclude(status=Appointment.Status.CANCELLED)
        .exists()
    )


def with_stats(qs):
    today = timezone.localdate()
    return qs.select_related("user").annotate(
        rating_avg=Avg("ratings__score"),
        rating_count=Count("ratings", distinct=True),
        open_slot_count=Count(
            "slots",
            filter=Q(slots__is_booked=False, slots__date__gte=today),
            distinct=True,
        ),
    )


def _keyword_hit(keyword, text):
    if " " in keyword or len(keyword) > 6:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def suggest_doctors(text):
    lowered = (text or "").lower()
    matched = []
    for label, keywords in SPECIALTY_KEYWORDS:
        hits = [word for word in keywords if _keyword_hit(word, lowered)]
        if hits:
            matched.append((label, hits))

    doctors = list(with_stats(DoctorProfile.objects.filter(is_approved=True, declined=False)))
    results = []
    fallback = False
    if matched:
        labels = {label for label, _ in matched}
        for doctor in doctors:
            blob = f"{doctor.specialty} {doctor.treats} {doctor.bio}".lower()
            reasons = []
            strength = 0
            for label, hits in matched:
                if doctor.specialty == label or label.lower() in blob or any(hit in blob for hit in hits):
                    reasons.append(label)
                    strength += len(hits) + (2 if doctor.specialty == label else 0)
            if doctor.specialty in labels or reasons:
                results.append((doctor, reasons or [doctor.specialty], strength))
        if not results:
            fallback = True
            results = [(doctor, ["General gynecology"], 0) for doctor in doctors if doctor.specialty == "General gynecology"]
            if not results:
                results = [(doctor, [], 0) for doctor in doctors]
    else:
        fallback = True
        results = [(doctor, [], 0) for doctor in doctors]

    results.sort(
        key=lambda item: (
            -item[2],
            -(item[0].rating_avg or 0),
            -item[0].open_slot_count,
            item[0].user.first_name,
        )
    )
    if matched and not fallback:
        message = ""
    elif matched and fallback:
        message = "No gynecologist lists that as their main work. Showing general gynecologists instead."
    else:
        message = "None of those words matched a specialty. Showing gynecologists on the site."
    return {
        "disclaimer": SUGGEST_DISCLAIMER,
        "fallback": fallback,
        "message": message,
        "matched_specialties": [label for label, _ in matched],
        "results": results[:6],
    }


def create_slots(doctor, day, start, end, minutes):
    if minutes < 10 or minutes > 180:
        raise ValueError("Use a slot length between 10 and 180 minutes.")
    if end <= start:
        raise ValueError("The end time has to be after the start time.")
    if day < timezone.localdate():
        raise ValueError("Choose today or a later date.")
    cursor = datetime.combine(day, start)
    stop = datetime.combine(day, end)
    created = []
    while cursor + timedelta(minutes=minutes) <= stop:
        slot_end = (cursor + timedelta(minutes=minutes)).time()
        slot_start = cursor.time()
        overlap = doctor.slots.filter(date=day, start_time__lt=slot_end, end_time__gt=slot_start).exists()
        if not overlap:
            created.append(
                Slot(doctor=doctor, date=day, start_time=slot_start, end_time=slot_end)
            )
        cursor += timedelta(minutes=minutes)
    if not created:
        raise ValueError("Those times overlap slots you already added, or the window is too short.")
    return Slot.objects.bulk_create(created)


def refresh_period_reminder(user):
    last = user.period_logs.order_by("-start_date").first()
    if not last:
        Reminder.objects.filter(user=user, kind=Reminder.Kind.PERIOD).delete()
        return
    try:
        cycle = user.patient_profile.cycle_length
    except Exception:
        cycle = 28
    next_on = last.start_date + timedelta(days=cycle)
    Reminder.objects.filter(user=user, kind=Reminder.Kind.PERIOD).delete()
    Reminder.objects.create(
        user=user,
        kind=Reminder.Kind.PERIOD,
        message=(
            f"Your next period may start around {next_on.strftime('%d %b %Y')}. "
            "This reminder uses only the dates you entered."
        ),
        due_on=next_on,
    )


def pregnancy_summary(log):
    if log is None:
        return None
    days = (timezone.localdate() - log.lmp).days
    weeks = max(0, days // 7)
    due = log.lmp + timedelta(days=280)
    return {
        "id": log.id,
        "lmp": log.lmp,
        "notes": log.notes,
        "is_active": log.is_active,
        "weeks": weeks,
        "due_date": due,
        "note": "Estimated from the date you entered. This is not a diagnosis or medical advice.",
    }


def refresh_pregnancy_reminder(user):
    log = user.pregnancy_logs.filter(is_active=True).first()
    if not log:
        Reminder.objects.filter(user=user, kind=Reminder.Kind.PREGNANCY).delete()
        return
    summary = pregnancy_summary(log)
    Reminder.objects.filter(user=user, kind=Reminder.Kind.PREGNANCY).delete()
    Reminder.objects.create(
        user=user,
        kind=Reminder.Kind.PREGNANCY,
        message=(
            f"About week {summary['weeks']} from the last-period date you saved. "
            f"Estimated due date {summary['due_date'].strftime('%d %b %Y')}. This is not medical advice."
        ),
        due_on=timezone.localdate(),
    )


def add_booking_reminders(appointment):
    when = (
        f"{appointment.slot.date.strftime('%d %b')} at "
        f"{appointment.slot.start_time.strftime('%I:%M %p')}"
    )
    doctor_name = appointment.doctor.user.get_full_name()
    Reminder.objects.create(
        user=appointment.patient,
        kind=Reminder.Kind.APPOINTMENT,
        appointment=appointment,
        due_on=appointment.slot.date,
        message=f"Clinic visit with Dr. {doctor_name} on {when}.",
    )
    if appointment.is_urgent:
        Reminder.objects.create(
            user=appointment.doctor.user,
            kind=Reminder.Kind.URGENT,
            appointment=appointment,
            due_on=appointment.slot.date,
            message=f"Urgent visit from {appointment.patient.first_name} on {when}. Pick this up first.",
        )
