from django.db import models
from django.conf import settings


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    avatar = models.ImageField(upload_to="profiles/avatars/", null=True, blank=True)

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
    avatar = models.ImageField(upload_to="specialists/avatars/", null=True, blank=True)
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
    file = models.ImageField(upload_to="profiles/documents/")
    status = models.CharField(
        max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return f"{self.specialist} → {self.file.name} ({self.status})"
