from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

from users.models import User

from rest_framework.exceptions import PermissionDenied


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get("email")

        if not email:
            return

        User = get_user_model()

        try:
            user = User.objects.get(email=email)

            if user.is_blocked:
                raise PermissionDenied("User is blocked")

            if not sociallogin.is_existing:
                sociallogin.connect(request, user)

        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if user.is_blocked:
            raise PermissionDenied("User is blocked")

        if not user.role:
            user.role = User.Roles.USER

        user.save()
        return user
