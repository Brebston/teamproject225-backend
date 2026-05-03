from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser

from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from events.api.v1.filters import EventFilter
from events.api.v1.permissions import IsOwnerOrReadOnly, IsSpecialistOrAdmin
from events.api.v1.serializers import (
    EventSerializer,
    CommentSerializer,
    CategorySerializer,
)
from events.models import (
    Event,
    Comment,
    CommentLike,
    EventLike,
    Category,
    EventImage,
)
from events.services import validate_event_images


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    parser_classes = [MultiPartParser, JSONParser, FormParser]
    permission_classes = [IsAuthenticatedOrReadOnly]


class EventViewSet(viewsets.ModelViewSet):
    queryset = (
        Event.objects.select_related(
            "author",
            "author__profile",
            "author__specialist_profile",
            "category",
        )
        .prefetch_related(
            "images",
            "likes",
            "comments",
        )
        .order_by("-created_at")
    )
    serializer_class = EventSerializer
    parser_classes = [MultiPartParser, JSONParser, FormParser]
    permission_classes = [IsSpecialistOrAdmin, IsOwnerOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    filterset_class = EventFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "likes_count"]
    ordering = ["-created_at"]

    def create(self, request, *args, **kwargs):
        images = request.FILES.getlist("images")

        # VALIDATION
        image_error = validate_event_images(images)
        if image_error:
            return Response(
                {"images": image_error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = serializer.save(author=request.user)

        # SAVE IMAGES
        for image in images:
            image.seek(0)
            EventImage.objects.create(event=event, image=image)

        return Response(
            self.get_serializer(event).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, pk=None):
        event = self.get_object()
        like, created = EventLike.objects.get_or_create(
            user=request.user, event=event
        )

        if not created:
            like.delete()
            return Response({"detail": "Event unliked"})

        return Response({"detail": "Event liked"})

    @action(
        detail=True,
        methods=["get", "post"],
        permission_classes=[IsAuthenticatedOrReadOnly],
    )
    def comments(self, request, pk=None):
        event = self.get_object()

        if request.method == "GET":
            comments = (
                Comment.objects.filter(event=event)
                .select_related("user")
                .prefetch_related("likes")
                .order_by("-created_at")
            )
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

        if request.method == "POST":
            serializer = CommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user, event=event)
            return Response(serializer.data, status=201)

        return Response({"detail": "Method Not Allowed"})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related("event", "user")
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=True, methods=["post"], permission_classes=[IsAuthenticated]
    )
    def like(self, request, pk=None):
        comment = self.get_object()
        like, created = CommentLike.objects.get_or_create(
            user=request.user, comment=comment
        )

        if not created:
            like.delete()
            return Response({"detail": "Comment unliked"})

        return Response({"detail": "Comment liked"})
