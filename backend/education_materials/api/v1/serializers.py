from rest_framework import serializers

from education_materials.models import (
    Article,
    ArticleSection,
    ArticleComment,
    VideoMaterial,
    VideoComment,
)


class ArticleSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleSection
        fields = [
            "id",
            "order",
            "title",
            "slug",
            "content",
        ]


class ArticleListSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    is_liked = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "cover_image",
            "status",
            "author",
            "published_at",
            "likes_count",
            "comments_count",
            "favorites_count",
            "is_liked",
            "is_favorite",
            "created_at",
        ]

    def get_is_liked(self, obj):
        user = self.context["request"].user

        if not user.is_authenticated:
            return False

        return obj.likes.filter(user=user).exists()

    def get_is_favorite(self, obj):
        user = self.context["request"].user

        if not user.is_authenticated:
            return False

        return user.favorites.filter(
            content_type__app_label=obj._meta.app_label,
            content_type__model=obj._meta.model_name,
            object_id=obj.id,
        ).exists()


class ArticleDetailSerializer(ArticleListSerializer):
    sections = ArticleSectionSerializer(many=True, read_only=True)

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + [
            "sections",
            "updated_at",
        ]


class ArticleCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "cover_image",
            "status",
            "published_at",
        ]
        read_only_fields = ["id", "slug"]


class ArticleCommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ArticleComment
        fields = [
            "id",
            "article",
            "user",
            "content",
            "likes_count",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "article",
            "user",
            "likes_count",
            "is_deleted",
            "created_at",
            "updated_at",
        ]


class VideoMaterialListSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    is_liked = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = VideoMaterial
        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "video_file",
            "status",
            "author",
            "published_at",
            "likes_count",
            "comments_count",
            "favorites_count",
            "is_liked",
            "is_favorite",
            "created_at",
        ]

    def get_is_liked(self, obj):
        user = self.context["request"].user

        if not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()

    def get_is_favorite(self, obj):
        user = self.context["request"].user

        if not user.is_authenticated:
            return False
        return user.favorites.filter(
            content_type__app_label=obj._meta.app_label,
            content_type__model=obj._meta.model_name,
            object_id=obj.id,
        ).exists()


class VideoMaterialDetailSerializer(VideoMaterialListSerializer):
    class Meta(VideoMaterialListSerializer.Meta):
        fields = VideoMaterialListSerializer.Meta.fields + [
            "updated_at",
        ]


class VideoMaterialCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoMaterial
        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "video_file",
            "status",
            "published_at",
        ]
        read_only_fields = ["id", "slug"]


class VideoCommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VideoComment
        fields = [
            "id",
            "video",
            "user",
            "content",
            "likes_count",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "video",
            "user",
            "likes_count",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
