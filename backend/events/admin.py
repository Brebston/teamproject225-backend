from django.contrib import admin

from events.models import (
    Category,
    Event,
    EventImage,
    EventLike,
    Comment,
    CommentLike,
)
from events.utils import get_user_full_name


class EventImageInline(admin.TabularInline):
    model = EventImage
    extra = 1
    max_num = 6


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "category",
        "author_full_name",
        "created_at",
    ]
    list_filter = ["category", "created_at"]
    search_fields = [
        "title",
        "description",
        "author__email",
        "author__first_name",
        "author__last_name",
    ]
    inlines = [EventImageInline]

    def author_full_name(self, obj):
        return get_user_full_name(obj.author)

    author_full_name.short_description = "Author"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "event",
        "user_full_name",
        "created_at",
    ]
    search_fields = [
        "text",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]

    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    user_full_name.short_description = "User"


admin.site.register(EventLike)
admin.site.register(CommentLike)
