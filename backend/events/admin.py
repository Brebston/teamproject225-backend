from django.contrib import admin

from events.models import Event, Category, EventImage, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "image")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("author", "category", "title", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("author__email",)
    ordering = ("-created_at",)


@admin.register(EventImage)
class EventImageAdmin(admin.ModelAdmin):
    list_display = ("event", "image")
    search_fields = ("event__title",)
    ordering = ("event",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "text", "created_at")
    search_fields = ("user",)
    list_filter = ("user", "event", "created_at")
    ordering = ("-created_at",)
