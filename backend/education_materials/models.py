from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

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
        upload_to="articles/covers", blank=True, null=True  # ??
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
        ordering = ["-published_at"]
        indexes = (
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-published_at"]),
        )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Article, self.title)

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
            self.slug = generate_unique_slug(ArticleSection, self.title)

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


class ArticleComment(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=300)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Article Comment"
        verbose_name_plural = "Article Comments"


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
