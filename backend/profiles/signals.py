from django.db.models.signals import post_save
from django.dispatch import receiver

from profiles.models import SpecialistProfile
from users.models import User


@receiver(post_save, sender=SpecialistProfile)
def update_user_role(sender, instance, **kwargs):
    """
    Signal receiver that updates the role of a user based on the verification status
    of their associated SpecialistProfile instance.

    This function listens to the `post_save` signal of the `SpecialistProfile` model.
    When a SpecialistProfile instance is saved, it checks if the verification status
    has changed the necessary role of the associated user and updates it accordingly.

    Parameters:
    sender: type
        The model class that triggered the signal. This is typically set automatically.
    instance: SpecialistProfile
        The instance of SpecialistProfile that was saved.
    **kwargs: dict
        Additional keyword arguments provided by the signal dispatcher, typically
        containing information such as `created` or `update_fields`.
    """
    user = instance.user

    new_role = (
        User.Roles.SPECIALIST if instance.is_verified else User.Roles.USER
    )

    if user.role != new_role:
        user.role = new_role
        user.save()
