from rest_framework.permissions import BasePermission

from .models import User


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.PATIENT
        )


class IsApprovedDoctor(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == User.Role.DOCTOR):
            return False
        profile = getattr(user, "doctor_profile", None)
        return bool(profile and profile.is_approved and not profile.declined)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN
        )
