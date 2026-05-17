from django.contrib import admin

from .models import AvailabilitySlot, Appointment


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ["id", "specialist", "start_time", "end_time", "is_booked", "created_at"]
    list_filter = ["is_booked", "specialist"]
    search_fields = ["specialist__first_name", "specialist__last_name"]
    ordering = ["start_time"]
    readonly_fields = ["created_at"]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user_profile",
        "specialist",
        "get_start_time",
        "status",
        "created_at",
        "updated_at",
        "cancelled_by",
        "cancelled_at"
    ]
    list_filter = ["status", "specialist"]
    search_fields = [
        "user_profile__first_name",
        "user_profile__last_name",
        "specialist__first_name",
        "specialist__last_name",
    ]
    ordering = ["slot__start_time"]
    readonly_fields = ["created_at", "updated_at", "cancelled_by", "cancelled_at"]

    @admin.display(description="Start time", ordering="slot__start_time")
    def get_start_time(self, obj):
        return obj.slot.start_time
