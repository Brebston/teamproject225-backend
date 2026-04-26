import os
import uuid

from django.db import models
from django.conf import settings

from phonenumber_field.modelfields import PhoneNumberField


def build_file_path(folder: str, extension: str) -> str:
    return os.path.join(f"uploads/{folder}", f"{uuid.uuid4()}{extension}")


def profile_avatar_file_path(instance, filename):
    _, ext = os.path.splitext(filename)
    return build_file_path("profiles/avatars", ext)


def specialist_avatar_file_path(instance, filename):
    _, ext = os.path.splitext(filename)
    return build_file_path("specialists/avatars", ext)


def specialist_document_file_path(instance, filename):
    _, ext = os.path.splitext(filename)
    return build_file_path("specialists/documents", ext)


class Profile(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    class Education(models.TextChoices):
        PSYCHOLOGIST = "psychologist", "Psychologist"
        TRAUMA_INFORMED_EDUCATOR = "trauma informed educator", "Trauma informed educator"
        OTHER = "other", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = PhoneNumberField(region="UA")
    city = models.CharField(max_length=150)
    birth_date = models.DateField()
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.PREFER_NOT_TO_SAY,
    )
    education = models.CharField(
        max_length=30,
        choices=Education.choices,
        default=Education.OTHER,
    )
    education_other = models.CharField(max_length=255, null=True, blank=True)
    cares_for_children = models.BooleanField(default=False)
    avatar = models.ImageField(
        upload_to=profile_avatar_file_path, null=True, blank=True
    )
    bio = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data_processing_consent_accepted_at = models.DateTimeField(null=True, blank=True)

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
    phone = PhoneNumberField(region="UA")
    city = models.CharField(max_length=150)
    specialisation = models.CharField(max_length=255)
    education = models.TextField()
    experience = models.TextField()
    bio = models.TextField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data_processing_consent_accepted_at = models.DateTimeField(null=True, blank=True)

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
