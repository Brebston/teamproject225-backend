from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticatedOrReadOnly,
    IsAuthenticated,
)
from rest_framework.response import Response

from education_materials.api.v1.permissions import (
    IsSpecialistOrAdminOrReadOnly,
    IsAuthorOrAdminOrReadOnly,
)
from education_materials.api.v1.serializers import (
    ArticleDetailSerializer,
    ArticleCreateUpdateSerializer,
    ArticleListSerializer,
    ArticleCommentSerializer,
)
from education_materials.models import (
    Article,
    ArticleLike,
    Favorite,
    ArticleComment,
    ArticleCommentLike,
)


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = (
        Article.objects.select_related("author")
        .prefetch_related("sections", "likes", "comments")
        .annotate(
            likes_count_db=Count("likes", distinct=True),
        )
        .order_by("-published_at", "-created_at")
    )
    lookup_field = "slug"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsSpecialistOrAdminOrReadOnly,
        IsAuthorOrAdminOrReadOnly,
    ]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ArticleDetailSerializer

        if self.action in ["create", "update", "partial_update"]:
            return ArticleCreateUpdateSerializer

        return ArticleListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, slug=None):
        article = self.get_object()

        like, created = ArticleLike.objects.get_or_create(
            user=request.user, article=article
        )

        if not created:
            like.delete()
            article.likes_count = article.likes.count()
            article.save(update_fields=["likes_count"])
            return Response({"detail": "Article unliked"})

        article.likes_count = article.likes.count()
        article.save(update_fields=["likes_count"])
        return Response({"detail": "Article liked"})

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, slug=None):
        article = self.get_object()
        content_type = ContentType.objects.get_for_model(article)

        favourite, created = Favorite.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=article.id,
        )

        if not created:
            favourite.delete()
            article.favorites_count = Favorite.objects.filter(
                content_type=content_type,
                object_id=article.id,
            ).count()
            article.save(update_fields=["favorites_count"])
            return Response({"detail": "Article removed from favorites"})

        article.favorites_count = Favorite.objects.filter(
            content_type=content_type,
            object_id=article.id,
        ).count()
        article.save(update_fields=["favorites_count"])
        return Response({"detail": "Article added to favorites"})

    @action(
        detail=True,
        methods=["get", "post"],
        permission_classes=[IsAuthenticatedOrReadOnly],
    )
    def comments(self, request, slug=None):
        article = self.get_object()

        if request.method == "GET":
            comments = (
                Article.objects.filter(article=article)
                .select_related("user")
                .annotate(likes_count=Count("likes", distinct=True))
                .order_by("-created_at")
            )
            serializer = ArticleCommentSerializer(comments, many=True)
            return Response(serializer.data)

        serializer = ArticleCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, article=article)
        article.comments_count = article.comments.count()
        article.save(update_fields=["comments_count"])
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ArticleCommentViewSet(viewsets.ModelViewSet):
    queryset = (
        ArticleComment.objects.select_related("article", "user")
        .annotate(likes_count=Count("likes", distinct=True))
        .order_by("-created_at")
    )
    serializer_class = ArticleCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, slug=None):
        comment = self.get_object()

        like, created = ArticleCommentLike.objects.get_or_create(
            user=request.user, comment=comment
        )

        if not created:
            like.delete()
            return Response({"detail": "Comment unliked"})

        return Response({"detail": "Comment liked"})
