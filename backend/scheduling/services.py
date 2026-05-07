from django.utils import timezone

from .models import Appointment


def mark_past_appointments_completed(queryset):
    """
    Lazily transition any CONFIRMED appointments whose slot has already ended
    to COMPLETED. Called inside get_queryset before returning to the caller.
    """
    now = timezone.now()

    stale_ids = list(
        queryset.filter(
            status=Appointment.Status.CONFIRMED,
            slot__end_time__lt=now,
        ).values_list("id", flat=True)
    )

    if stale_ids:
        Appointment.objects.filter(id__in=stale_ids).update(
            status=Appointment.Status.COMPLETED
        )

    return queryset
