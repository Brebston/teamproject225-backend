from rest_framework import serializers

from events.models import Category, EventImage, Event, Comment


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "image"]


class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ["id", "image"]


class EventSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        write_only=True,
        source="category",
    )
    category = CategorySerializer(read_only=True)
    images = EventImageSerializer(many=True, required=False)
    likes_count = serializers.IntegerField(
        source="likes.count", read_only=True
    )
    comments_count = serializers.IntegerField(
        source="comments.count", read_only=True
    )
    author_name = serializers.CharField(
        source="author.get_full_name", read_only=True
    )

    class Meta:
        model = Event
        fields = [
            "id",
            "category_id",
            "category",
            "title",
            "description",
            "images",
            "likes_count",
            "comments_count",
            "author_name",
            "created_at",
        ]

    def validate_images(self, value):
        if len(value) > 6:
            raise serializers.ValidationError("Max 6 images allowed")
        return value

    def create(self, validated_data):
        images_data = validated_data.pop("images", [])
        request = self.context.get("request")
        event = Event.objects.create(author=request.user, **validated_data)

        for image in images_data:
            EventImage.objects.create(event=event, **image)

        return event


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source="user.get_full_name", read_only=True
    )
    user_avatar = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(
        source="likes.count", read_only=True
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "event",
            "text",
            "user_name",
            "user_avatar",
            "likes_count",
            "created_at",
        ]

        extra_kwargs = {"user": {"read_only": True}}

    def get_user_avatar(self, obj):
        if hasattr(obj.user, "avatar") and obj.user.profile.avatar:
            return obj.user.avatar.url
        return None
