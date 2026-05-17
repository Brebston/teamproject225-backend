from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticatedOrReadOnly,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError

from education_materials.api.v1.permissions import (
    IsSpecialistOrAdminOrReadOnly,
    IsAuthorOrAdminOrReadOnly,
)
from education_materials.api.v1.serializers import (
    ArticleDetailSerializer,
    ArticleCreateUpdateSerializer,
    ArticleListSerializer,
    ArticleCommentSerializer,
    VideoMaterialDetailSerializer,
    VideoMaterialCreateUpdateSerializer,
    VideoCommentSerializer,
    VideoMaterialListSerializer,
)
from education_materials.models import (
    Article,
    ArticleLike,
    Favorite,
    ArticleComment,
    ArticleCommentLike,
    VideoMaterial,
    VideoLike,
    VideoComment,
    VideoCommentLike,
)


class ArticleViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsSpecialistOrAdminOrReadOnly,
        IsAuthorOrAdminOrReadOnly,
    ]
    http_method_names = ["get", "post", "delete", "patch"]

    def get_queryset(self):
        queryset = (
            Article.objects.select_related("author")
            .prefetch_related(
                "sections",
            )
            .order_by("-published_at", "-created_at")
        )

        user = self.request.user

        if not user.is_authenticated:
            return queryset.filter(status=Article.Status.PUBLISHED)

        if user.role in ["admin", "moderator"]:
            return queryset

        return queryset.filter(
            Q(status=Article.Status.PUBLISHED) | Q(author=user)
        )

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

        if article.status != Article.Status.PUBLISHED:
            raise NotFound("Article not found")

        like, created = ArticleLike.objects.get_or_create(
            user=request.user,
            article=article,
        )

        if not created:
            like.delete()
            article.refresh_from_db()

            return Response(
                {
                    "detail": "Article unliked",
                    "likes_count": article.likes_count,
                }
            )

        article.refresh_from_db()

        return Response(
            {
                "detail": "Article liked",
                "likes_count": article.likes_count,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, slug=None):
        article = self.get_object()

        if article.status != Article.Status.PUBLISHED:
            raise NotFound("Article not found")

        content_type = ContentType.objects.get_for_model(article)

        favourite, created = Favorite.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=article.id,
        )

        if not created:
            favourite.delete()
            article.refresh_from_db()
            return Response({"detail": "Article removed from favorites"})

        article.refresh_from_db()
        return Response({"detail": "Article added to favorites"})

    @action(
        detail=True,
        methods=["get", "post"],
        permission_classes=[IsAuthenticatedOrReadOnly],
    )
    def comments(self, request, slug=None):
        article = self.get_object()

        if article.status != Article.Status.PUBLISHED:
            raise NotFound("Article not found")

        if request.method == "GET":
            comments = (
                ArticleComment.objects.filter(
                    article=article, is_deleted=False
                )
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
        .filter(is_deleted=False)
        .annotate(likes_count=Count("likes", distinct=True))
        .order_by("-created_at")
    )
    serializer_class = ArticleCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrAdminOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.is_deleted:
            raise ValidationError(
                {"detail": "Deleted comments cannot be edited"}
            )

        serializer.save()

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, pk=None):
        comment = self.get_object()

        like, created = ArticleCommentLike.objects.get_or_create(
            user=request.user, comment=comment
        )

        if not created:
            like.delete()
            return Response({"detail": "Comment unliked"})

        return Response({"detail": "Comment liked"})


class VideoMaterialViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsSpecialistOrAdminOrReadOnly,
        IsAuthorOrAdminOrReadOnly,
    ]
    http_method_names = ["get", "post", "delete", "patch"]

    def get_queryset(self):
        queryset = VideoMaterial.objects.select_related("author").order_by(
            "-published_at", "-created_at"
        )

        user = self.request.user

        if not user.is_authenticated:
            return queryset.filter(status=VideoMaterial.Status.PUBLISHED)

        if user.role in ["admin", "moderator"]:
            return queryset

        return queryset.filter(
            Q(status=VideoMaterial.Status.PUBLISHED) | Q(author=user)
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return VideoMaterialDetailSerializer

        if self.action in ["create", "update", "partial_update"]:
            return VideoMaterialCreateUpdateSerializer

        if self.action == "comments":
            return VideoCommentSerializer

        return VideoMaterialListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def ensure_published(self, video):
        if video.status != VideoMaterial.Status.PUBLISHED:
            raise NotFound("Video not found")

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, slug=None):
        video = self.get_object()
        self.ensure_published(video)

        like, created = VideoLike.objects.get_or_create(
            user=request.user,
            video=video,
        )

        if not created:
            like.delete()
            video.refresh_from_db()
            return Response(
                {
                    "detail": "Video unliked",
                    "likes_count": video.likes_count,
                }
            )

        video.refresh_from_db()
        return Response(
            {
                "detail": "Video liked",
                "likes_count": video.likes_count,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, slug=None):
        video = self.get_object()
        self.ensure_published(video)

        content_type = ContentType.objects.get_for_model(video)

        favourite, created = Favorite.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=video.id,
        )

        if not created:
            favourite.delete()
            video.refresh_from_db()
            return Response(
                {
                    "detail": "Video removed from favorites",
                    "favorites_count": video.favorites_count,
                }
            )

        video.refresh_from_db()
        return Response(
            {
                "detail": "Video added to favorites",
                "favorites_count": video.favorites_count,
            }
        )

    @action(
        detail=True,
        methods=["get", "post"],
        permission_classes=[IsAuthenticatedOrReadOnly],
    )
    def comments(self, request, slug=None):
        video = self.get_object()

        if request.method == "GET":
            comments = (
                VideoComment.objects.filter(video=video, is_deleted=False)
                .select_related("user")
                .annotate(likes_count=Count("likes", distinct=True))
                .order_by("-created_at")
            )
            serializer = VideoCommentSerializer(comments, many=True)
            return Response(serializer.data)

        self.ensure_published(video)

        serializer = VideoCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, video=video)

        video.refresh_from_db()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VideoCommentViewSet(viewsets.ModelViewSet):
    queryset = (
        VideoComment.objects.select_related("video", "user")
        .filter(is_deleted=False)
        .annotate(likes_count=Count("likes", distinct=True))
        .order_by("-created_at")
    )
    serializer_class = VideoCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrAdminOrReadOnly]
    http_method_names = ["get", "post", "delete", "patch"]

    def perform_update(self, serializer):
        if serializer.instance.is_deleted:
            raise ValidationError(
                {"detail": "Deleted comments cannot be edited"}
            )

        serializer.save()

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, pk=None):
        comment = self.get_object()

        if comment.video.status != VideoMaterial.Status.PUBLISHED:
            raise NotFound("Video not found")

        like, created = VideoCommentLike.objects.get_or_create(
            user=request.user, comment=comment
        )

        if not created:
            like.delete()
            return Response({"detail": "Comment unliked"})

        return Response({"detail": "Comment liked"})
