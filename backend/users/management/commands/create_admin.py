from os import getenv

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        email = getenv("ADMIN_EMAIL")
        password = getenv("ADMIN_PASSWORD")

        if not email or not password:
            return

        if User.objects.filter(email=email).exists():
            return

        User.objects.create_superuser(
            email=email,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Superuser '{email}' created")
        )