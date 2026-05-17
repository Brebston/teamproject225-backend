from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from profiles.models import Profile, SpecialistProfile
from users.models import User


class AvailabilitySlot(models.Model):
    specialist = models.ForeignKey(
        SpecialistProfile,
        on_delete=models.CASCADE,
        related_name="availability_slots",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Availability Slot"
        verbose_name_plural = "Availability Slots"
        ordering = ["start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["specialist", "start_time"],
                name="unique_specialist_slot",
            )
        ]

    def clean(self):
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            if duration != 3600:
                raise ValidationError("Slots must be exactly 60 minutes.")
            if self.start_time < timezone.now():
                raise ValidationError("Cannot create slots in the past.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.specialist} — {self.start_time:%Y-%m-%d %H:%M}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    slot = models.ForeignKey(
        AvailabilitySlot,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    specialist = models.ForeignKey(
        SpecialistProfile,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    user_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_appointments",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ["slot__start_time"]

    def __str__(self):
        return f"{self.user_profile} → {self.specialist} @ {self.slot.start_time:%Y-%m-%d %H:%M}"
