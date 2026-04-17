from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from users.models import User

from rest_framework.exceptions import PermissionDenied


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.user.email

        if email:
            existing_user = User.objects.filter(email__iexact=email).first()

            if existing_user:
                if existing_user and existing_user.is_blocked:
                    raise ParseError("User is blocked")

            sociallogin.connect(request, existing_user)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if not user.role:
            user.role = User.Roles.USER

        user.save()
        return user
