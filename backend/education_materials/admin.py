from django.contrib import admin
from django.utils.text import Truncator

from education_materials.models import (
    Article,
    ArticleSection,
    ArticleLike,
    ArticleComment,
    ArticleCommentLike,
    Favorite,
    VideoMaterial,
    VideoLike,
    VideoComment,
    VideoCommentLike,
)


class ArticleSectionInline(admin.StackedInline):
    model = ArticleSection
    extra = 1


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "author",
        "status",
        "published_at",
        "likes_count",
        "comments_count",
        "favorites_count",
    ]
    list_filter = ["status", "created_at", "published_at"]
    search_fields = ["title", "author__email"]
    inlines = [
        ArticleSectionInline,
    ]
    ordering = ("-created_at",)
    exclude = ["slug"]

    def get_exclude(self, request, obj=None):
        exclude = ["slug"]

        if obj is None:
            exclude += ["likes_count", "comments_count", "favorites_count"]

        return exclude

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "likes_count",
                "comments_count",
                "favorites_count",
                "created_at",
                "updated_at",
            )

        return ()


@admin.register(ArticleComment)
class ArticleCommentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "article",
        "user_full_name",
        "short_content",
        "created_at",
        "edited_at",
    ]
    list_filter = ["created_at"]
    search_fields = ["content", "user__email"]
    ordering = ("-created_at",)

    def short_content(self, obj):
        if len(obj.content) > 15:
            return obj.content[:15] + "..."
        return obj.content

    short_content.short_description = "Comment"

    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    user_full_name.short_description = "User"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "content_object",
        "created_at",
    )

    readonly_fields = (
        "user",
        "content_type",
        "object_id",
        "created_at",
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ArticleLike)
class ArticleLikeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_full_name",
        "article",
        "created_at",
    )

    readonly_fields = (
        "user",
        "article",
        "created_at",
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    user_full_name.short_description = "User"


@admin.register(ArticleCommentLike)
class ArticleCommentLikeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_full_name",
        "short_content",
        "created_at",
    )
    readonly_fields = (
        "user",
        "comment",
        "created_at",
    )
    ordering = ("-created_at",)
    list_select_related = ("user", "comment")

    def short_content(self, obj):
        return Truncator(obj.comment.content).chars(15)

    short_content.short_description = "Comment"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    user_full_name.short_description = "User"


@admin.register(VideoMaterial)
class VideoMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "status",
        "published_at",
        "likes_count",
        "comments_count",
        "favorites_count",
    )
    list_filter = ["status", "created_at", "published_at"]
    search_fields = ["title", "short_description", "author__email"]
    ordering = (
        "-published_at",
        "-created_at",
    )
    exclude = ["slug"]

    def get_exclude(self, request, obj=None):
        exclude = ["slug"]

        if obj is None:
            exclude += ["likes_count", "comments_count", "favorites_count"]

        return exclude

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "likes_count",
                "comments_count",
                "favorites_count",
                "created_at",
                "updated_at",
            )

        return ()


@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_full_name",
        "video",
        "created_at",
    )
    readonly_fields = (
        "user",
        "video",
        "created_at",
    )
    ordering = ("-created_at",)
    list_select_related = ("user", "video")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    user_full_name.short_description = "User"


@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "video",
        "user_full_name",
        "short_content",
        "created_at",
    )
    list_filter = ["created_at"]
    search_fields = ("content", "user__email", "video__title")
    ordering = ("-created_at",)
    list_select_related = ("user", "video")

    def short_content(self, obj):
        return Truncator(obj.content).chars(15)

    short_content.short_description = "Comment"

    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    user_full_name.short_description = "User"


@admin.register(VideoCommentLike)
class VideoCommentLikeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_full_name",
        "short_comment",
        "created_at",
    )
    readonly_fields = (
        "user",
        "comment",
        "created_at",
    )
    ordering = ("-created_at",)
    list_select_related = ("user", "comment")

    def short_comment(self, obj):
        return Truncator(obj.comment.content).chars(15)

    short_comment.short_description = "Comment"

    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    user_full_name.short_description = "User"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
