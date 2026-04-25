from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_password_reset_email(email, reset_link):
    send_mail(
        subject="Password reset",
        message=f"To reset your password, open this link:\n\n{reset_link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
