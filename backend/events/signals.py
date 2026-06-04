from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from education_materials.models import Favorite
from events.models import Event


def update_event_favorites_count(event):
    event.favorites_count = Favorite.objects.filter(
        content_type__app_label=event._meta.app_label,
        content_type__model=event._meta.model_name,
        object_id=event.id,
    ).count()
    event.save(update_fields=["favorites_count"])


@receiver(post_save, sender=Favorite)
def favorite_created(sender, instance, **kwargs):
    content_object = instance.content_object

    if isinstance(content_object, Event):
        update_event_favorites_count(content_object)


@receiver(post_delete, sender=Favorite)
def favorite_deleted(sender, instance, **kwargs):
    content_object = instance.content_object

    if isinstance(content_object, Event):
        update_event_favorites_count(content_object)
