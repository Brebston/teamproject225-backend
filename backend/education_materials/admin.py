from django.contrib import admin

from education_materials.models import (
    Article,
    ArticleSection,
    ArticleLike,
    ArticleComment,
    ArticleCommentLike,
    Favorite,
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
        "created_at",
    ]
    list_filter = ["status", "created_at", "published_at"]
    search_fields = ["title", "author__email"]
    inlines = [
        ArticleSectionInline,
    ]
    readonly_fields = [
        "likes_count",
        "comments_count",
        "favorites_count",
        "created_at",
        "updated_at",
    ]
    exclude = ["slug"]


admin.site.register(ArticleLike)
admin.site.register(ArticleComment)
admin.site.register(ArticleCommentLike)
admin.site.register(Favorite)
