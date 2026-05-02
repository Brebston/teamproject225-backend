from rest_framework import serializers

from events.models import Category, EventImage, Event, Comment
from events.utils import get_user_full_name, get_user_avatar


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "image"]


class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ["id", "image"]


class EventSerializer(serializers.ModelSerializer):
    description = serializers.CharField(max_length=300)
    images = EventImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True
    )
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    author_full_name = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_name",
            "author",
            "author_full_name",
            "images",
            "likes_count",
            "comments_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "created_at", "updated_at"]

    def get_author_full_name(self, obj):
        return get_user_full_name(obj.author)


class CommentSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "event",
            "user",
            "user_full_name",
            "user_avatar",
            "text",
            "likes_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["user", "created_at", "updated_at"]

    def get_user_full_name(self, obj):
        return get_user_full_name(obj.user)

    def get_user_avatar(self, obj):
        return get_user_avatar(obj.user)
