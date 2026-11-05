from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AccessLog, Article, Complaint, DoctorProfile, ForumPost, User

# Medical records stay out of the Django admin. The product admin does not read them.


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("SheCares", {"fields": ("role", "phone", "forum_name")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("SheCares", {"fields": ("email", "role", "phone", "forum_name")}),
    )
    ordering = ("email",)


admin.site.register(DoctorProfile)
admin.site.register(Article)
admin.site.register(ForumPost)
admin.site.register(Complaint)
admin.site.register(AccessLog)
