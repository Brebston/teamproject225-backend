import os

from django.conf import settings
from django.db import models

from events.utils import get_user_full_name
from profiles.models import build_file_path

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Event"
        verbose_name_plural = "Events"

    @property
    def get_author_full_name(self):
        return f"{self.author.first_name} {self.author.last_name}"

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()

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
