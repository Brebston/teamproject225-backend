from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.text import Truncator
from django_ckeditor_5.fields import CKEditor5Field
from slugify import slugify

from education_materials.api.v1.utils import generate_unique_slug

User = settings.AUTH_USER_MODEL


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="articles"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    cover_image = models.ImageField(
        upload_to="uploads/education_materials/article_images",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    favorites_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ["-published_at", "-created_at"]
        indexes = (
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-published_at"]),
        )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Article, self.title)

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ArticleSection(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="sections"
    )
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    content = CKEditor5Field(config_name="extends")

    class Meta:
        verbose_name = "Article Section"
        verbose_name_plural = "Article Sections"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["article", "slug"],
                name="unique_article_section_slug",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ArticleLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Article Like"
        verbose_name_plural = "Article Likes"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "article"],
                name="unique_article_like",
            )
        ]

    def __str__(self):
        profile = getattr(self.user, "profile", None)
        specialist = getattr(self.user, "specialist_profile", None)

        if profile:
            name = f"{profile.first_name} {profile.last_name}".strip()
        elif specialist:
            name = f"{specialist.first_name} {specialist.last_name}".strip()
        else:
            name = self.user.email

        return f"{name} liked {self.article.title}"


class ArticleComment(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=300)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Article Comment"
        verbose_name_plural = "Article Comments"

    def save(self, *args, **kwargs):
        if self.pk:
            self.edited_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return Truncator(self.content).chars(50)


class ArticleCommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(
        ArticleComment, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Article Comment Like"
        verbose_name_plural = "Article Comment Likes"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "comment"],
                name="unique_article_comment_like",
            )
        ]

    def __str__(self):
        profile = getattr(self.user, "profile", None)
        specialist = getattr(self.user, "specialist_profile", None)

        if profile:
            name = f"{profile.first_name} {profile.last_name}".strip()
        elif specialist:
            name = f"{specialist.first_name} {specialist.last_name}".strip()
        else:
            name = self.user.email

        return f"{name} liked {Truncator(self.comment.content).chars(15)}"


class Favorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="favorites"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"
        unique_together = ("user", "content_type", "object_id")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"],
                name="unique_user_favorite",
            )
        ]

    def __str__(self):
        return f"{self.user.email} favorite {self.content_object}"


class VideoMaterial(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="video_materials"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    short_description = models.TextField(max_length=300)
    video_file = models.FileField(
        upload_to="uploads/education_materials/video_materials",
        validators=[FileExtensionValidator(["mp4", "avi", "mov", "webm"])],
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    favorites_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Video Material"
        verbose_name_plural = "Video Materials"
        ordering = ["-published_at"]
        indexes = (
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-published_at"]),
        )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(VideoMaterial, self.title)

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class VideoLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(
        VideoMaterial, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Video Like"
        verbose_name_plural = "Video Likes"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "video"],
                name="unique_video_like",
            )
        ]

    def __str__(self):
        profile = getattr(self.user, "profile", None)
        specialist = getattr(self.user, "specialist_profile", None)

        if profile:
            name = f"{profile.first_name} {profile.last_name}".strip()
        elif specialist:
            name = f"{specialist.first_name} {specialist.last_name}".strip()
        else:
            name = self.user.email

        return f"{name} liked {self.video.title}"


class VideoComment(models.Model):
    video = models.ForeignKey(
        VideoMaterial, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=300)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Video Comment"
        verbose_name_plural = "Video Comments"

    def save(self, *args, **kwargs):
        if self.pk:
            self.edited_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return Truncator(self.content).chars(50)


class VideoCommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(
        VideoComment, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Video Comment Like"
        verbose_name_plural = "Video Comment Likes"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "comment"],
                name="unique_video_comment_like",
            )
        ]

    def __str__(self):
        profile = getattr(self.user, "profile", None)
        specialist = getattr(self.user, "specialist_profile", None)

        if profile:
            name = f"{profile.first_name} {profile.last_name}".strip()
        elif specialist:
            name = f"{specialist.first_name} {specialist.last_name}".strip()
        else:
            name = self.user.email

        return f"{name} liked {Truncator(self.comment.content).chars(15)}"
