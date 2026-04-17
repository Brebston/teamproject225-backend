import os
import uuid

from django.db import models
from django.conf import settings
from django.utils.text import slugify


def build_file_path(folder: str, name_slug: str, extension: str) -> str:
    return os.path.join(f"uploads/{folder}", f"{name_slug}-{uuid.uuid4()}{extension}")


def make_upload_path(folder: str, last_name_attr: str = "last_name"):
    def handler(instance, filename):
        _, ext = os.path.splitext(filename)
        obj = instance
        for attr in last_name_attr.split("."):
            obj = getattr(obj, attr)
        return build_file_path(folder, slugify(obj), ext)
    return handler


profile_avatar_file_path = make_upload_path("profiles/avatars")
specialist_avatar_file_path = make_upload_path("specialists/avatars")
specialist_document_file_path = make_upload_path("specialists/documents", "specialist.last_name")


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    avatar = models.ImageField(
        upload_to=profile_avatar_file_path, null=True, blank=True
    )

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class SpecialistProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="specialist_profile",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    avatar = models.ImageField(upload_to=specialist_avatar_file_path, null=True, blank=True)
    education = models.TextField()
    experience = models.TextField()
    specialisation = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Specialist Profile"
        verbose_name_plural = "Specialist Profiles"

    def __str__(self):
        return f"Specialist: {self.first_name} {self.last_name}"


class Document(models.Model):
    class DocumentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    specialist = models.ForeignKey(
        SpecialistProfile, on_delete=models.CASCADE, related_name="documents"
    )
    file = models.ImageField(upload_to=specialist_document_file_path)
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return f"{self.specialist} → {self.file.name} ({self.status})"
