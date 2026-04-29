from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.decorators import action

from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from events.api.v1.permissions import IsOwnerOrReadOnly
from events.api.v1.serializers import EventSerializer, CommentSerializer
from events.models import Event, Comment, CommentLike, EventLike


class EventViewSet(viewsets.ModelViewSet):
    queryset = (
        Event.objects.all()
        .select_related("category", "author")
        .prefetch_related("images", "likes", "comments")
    )
    serializer_class = EventSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        return [IsAuthenticatedOrReadOnly()]

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        event = self.get_object()
        like, created = EventLike.objects.get_or_create(
            user=request.user, event=event
        )

        if not created:
            like.delete()
            return Response({"liked": False})

        return Response({"liked": True})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related(
        "user", "event"
    ).prefetch_related("likes")
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        comment = self.get_object()
        like, created = CommentLike.objects.get_or_create(
            user=request.user, comment=comment
        )

        if not created:
            like.delete()
            return Response({"liked": False})

        return Response({"liked": True})
