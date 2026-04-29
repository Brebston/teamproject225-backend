import os

from django.conf import settings
from django.db import models

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

    def __str__(self):
        return self.name


class Event(models.Model):
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="events"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="events"
    )
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

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


class Comments(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="comments"
    )
    text = models.TextField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} -> {self.event}"


class CommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(
        Comments, on_delete=models.CASCADE, related_name="likes"
    )

    class Meta:
        unique_together = ("user", "comment")

    def __str__(self):
        return f"{self.user} likes comment {self.comment.id}"
