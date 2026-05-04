import os

from django.conf import settings
from django.db import models

from phonenumber_field.modelfields import PhoneNumberField

from profiles.models import build_file_path, Profile

User = settings.AUTH_USER_MODEL


def category_image_file_path(instance, filename):
    _, ext = os.path.splitext(filename)
    return build_file_path("events/category_images", ext)


def event_image_file_path(instance, filename):
    _, ext = os.path.splitext(filename)
    return build_file_path("events/event_images", ext)


class Category(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(
        upload_to=category_image_file_path, blank=True, null=True
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=300)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="events"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="events"
    )
    max_participants = models.PositiveIntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Event"
        verbose_name_plural = "Events"

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()

    @property
    def registrations_count(self):
        return self.registrations.count()

    def __str__(self):
        return self.title


class EventImage(models.Model):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to=event_image_file_path, blank=True, null=True
    )

    def __str__(self):
        return f"Image for {self.event.id}"


class EventLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="likes"
    )

    class Meta:
        unique_together = ("user", "event")
        verbose_name = "Event like"
        verbose_name_plural = "Event likes"

    def __str__(self):
        profile = getattr(self.user, "profile", None)
        specialist = getattr(self.user, "specialist_profile", None)

        if profile:
            name = f"{profile.first_name} {profile.last_name}".strip()
        elif specialist:
            name = f"{specialist.first_name} {specialist.last_name}".strip()
        else:
            name = self.user.email

        return f"{name} liked {self.event.title}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="comments"
    )
    text = models.TextField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    @property
    def likes_count(self):
        return self.likes.count()

    def __str__(self):
        return f"{self.user} -> {self.event}"


class CommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="likes"
    )

    class Meta:
        unique_together = ("user", "comment")
        verbose_name = "Comment like"
        verbose_name_plural = "Comment likes"

    def __str__(self):
        return f"{self.user} likes comment {self.comment.id}"


class EventRegistration(models.Model):
    class Experience(models.TextChoices):
        PARENTS = "parents", "Parents"
        TEACHER = "teacher", "Teacher"
        PSYCHOLOGIST = "psychologist", "Psychologist"
        TRAUMA_PEDAGOGY = "trauma_pedagogy", "Trauma pedagogy"
        SOCIAL_WORKER = "social_worker", "Social worker"
        OTHER = "other", "Other"

    event = models.ForeignKey(
        "Event",
        on_delete=models.CASCADE,
        related_name="registrations",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_registrations",
    )

    full_name = models.CharField(max_length=255)
    birth_date = models.DateField()
    gender = models.CharField(
        max_length=20,
        choices=Profile.Gender.choices,
        default=Profile.Gender.PREFER_NOT_TO_SAY,
    )
    phone = PhoneNumberField(region="UA")
    email = models.EmailField()
    experience = models.CharField(
        max_length=50,
        choices=Experience.choices,
    )
    eating_meat = models.BooleanField()
    is_agreed = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "email"],
                name="unique_event_email",
            )
        ]

    def __str__(self):
        return f"{self.full_name} → {self.event.title}"
