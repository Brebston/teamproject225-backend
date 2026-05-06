from celery import shared_task
from django.utils import timezone


@shared_task
def delete_unbooked_past_slots():
    """
    Deletes all unbooked slots whose start_time is in the past.
    Safe to run at any frequency — booked slots are never touched.
    Scheduled nightly via CELERY_BEAT_SCHEDULE in settings.
    """
    from .models import AvailabilitySlot

    deleted_count, _ = AvailabilitySlot.objects.filter(
        is_booked=False,
        start_time__lt=timezone.now(),
    ).delete()

    return f"Deleted {deleted_count} unbooked past slot(s)."
