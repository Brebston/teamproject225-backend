from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "email",
        "role",
        "is_blocked",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_blocked",
        "is_staff",
        "is_active",
    )

    search_fields = ("email",)
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "is_blocked",
                    "is_staff",
                    "is_active",
                    "is_superuser",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role"),
            },
        ),
    )
