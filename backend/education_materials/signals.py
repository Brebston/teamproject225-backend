from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from education_materials.models import (
    ArticleLike,
    ArticleComment,
    Favorite,
    Article,
    VideoLike,
    VideoComment,
    VideoMaterial,
)


def update_article_likes_count(article):
    article.likes_count = ArticleLike.objects.filter(article=article).count()
    article.save(update_fields=["likes_count"])


def update_article_comments_count(article):
    article.comments_count = ArticleComment.objects.filter(
        article=article,
        is_deleted=False,
    ).count()
    article.save(update_fields=["comments_count"])


def update_article_favorites_count(article):
    article.favorites_count = Favorite.objects.filter(
        content_type__app_label=article._meta.app_label,
        content_type__model=article._meta.model_name,
        object_id=article.id,
    ).count()
    article.save(update_fields=["favorites_count"])


def update_video_likes_count(video):
    video.likes_count = VideoLike.objects.filter(video=video).count()
    video.save(update_fields=["likes_count"])


def update_video_comments_count(video):
    video.comments_count = VideoComment.objects.filter(
        video=video, is_deleted=False
    ).count()
    video.save(update_fields=["comments_count"])


def update_video_favorites_count(video):
    video.favorites_count = Favorite.objects.filter(
        content_type__app_label=video._meta.app_label,
        content_type__model=video._meta.model_name,
        object_id=video.id,
    ).count()
    video.save(update_fields=["favorites_count"])


@receiver(post_save, sender=ArticleLike)
def article_like_created(sender, instance, **kwargs):
    update_article_likes_count(instance.article)


@receiver(post_delete, sender=ArticleLike)
def article_like_deleted(sender, instance, **kwargs):
    update_article_likes_count(instance.article)


@receiver(post_save, sender=ArticleComment)
def article_comment_created(sender, instance, **kwargs):
    update_article_comments_count(instance.article)


@receiver(post_delete, sender=ArticleComment)
def article_comment_deleted(sender, instance, **kwargs):
    update_article_comments_count(instance.article)


@receiver(post_save, sender=Favorite)
def favourite_created(sender, instance, **kwargs):
    content_object = instance.content_object

    if isinstance(content_object, Article):
        update_article_favorites_count(content_object)

    if isinstance(content_object, VideoMaterial):
        update_video_favorites_count(content_object)


@receiver(post_delete, sender=Favorite)
def favourite_deleted(sender, instance, **kwargs):
    content_object = instance.content_object

    if isinstance(content_object, Article):
        update_article_favorites_count(content_object)

    if isinstance(content_object, VideoMaterial):
        update_video_favorites_count(content_object)


@receiver(post_save, sender=VideoLike)
def video_like_created(sender, instance, **kwargs):
    update_video_likes_count(instance.video)


@receiver(post_delete, sender=VideoLike)
def video_like_deleted(sender, instance, **kwargs):
    update_video_likes_count(instance.video)


@receiver(post_save, sender=VideoComment)
def video_comment_created(sender, instance, **kwargs):
    update_video_comments_count(instance.video)


@receiver(post_delete, sender=VideoComment)
def video_comment_deleted(sender, instance, **kwargs):
    update_video_comments_count(instance.video)
