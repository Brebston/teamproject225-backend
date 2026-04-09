from django.contrib import admin
from .models import Profile, SpecialistProfile, Document


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name", "last_name", "avatar")
    search_fields = ("first_name", "last_name", "user__email")
    ordering = ("last_name",)


@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "first_name",
        "last_name",
        "specialisation",
        "is_verified",
    )
    list_filter = ("is_verified", "specialisation")
    search_fields = (
        "first_name",
        "last_name",
        "user__email",
        "specialisation",
    )
    ordering = ("last_name",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("specialist", "file", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = (
        "specialist__first_name",
        "specialist__last_name",
        "specialist__user__email",
    )
    ordering = ("-created_at",)
