from django.db import models
from rest_framework import viewsets, permissions, serializers
from rest_framework.permissions import AllowAny

from users.api.v1.permissions import IsNotBlocked, IsOwnerOrStaff
from users.models import User
from .models import Profile, SpecialistProfile, Document
from .serializers import (
    ProfileCreateSerializer,
    ProfileUpdateSerializer,
    ProfileListSerializer,
    ProfileDetailSerializer,
    SpecialistProfileCreateSerializer,
    SpecialistProfileUpdateSerializer,
    SpecialistProfileListSerializer,
    SpecialistProfileDetailSerializer,
    SpecialistProfileModeratorSerializer,
    DocumentSerializer,
    DocumentModeratorSerializer,
)

ADMIN_ROLES = [User.Roles.ADMIN, User.Roles.MODERATOR]


class ProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsNotBlocked]

    def get_permissions(self):
        if self.action in ("retrieve", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsNotBlocked(), IsOwnerOrStaff()]
        return [permissions.IsAuthenticated(), IsNotBlocked()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role in ADMIN_ROLES:
            return Profile.objects.all()
        return Profile.objects.filter(user=user)

    def get_serializer_class(self):
        return {
            "create": ProfileCreateSerializer,
            "update": ProfileUpdateSerializer,
            "partial_update": ProfileUpdateSerializer,
            "list": ProfileListSerializer,
            "retrieve": ProfileDetailSerializer,
        }.get(self.action, ProfileDetailSerializer)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != user.Roles.USER:
            raise serializers.ValidationError(
                {"detail": "Only users can create a regular profile."}
            )
        if hasattr(user, "profile"):
            raise serializers.ValidationError(
                {"detail": "You already have a profile."}
            )
        serializer.save(user=user)


class SpecialistProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsNotBlocked]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsNotBlocked(), IsOwnerOrStaff()]
        return [permissions.IsAuthenticated(), IsNotBlocked()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.role in ADMIN_ROLES:
                return SpecialistProfile.objects.all()
            return SpecialistProfile.objects.filter(
                models.Q(is_verified=True) | models.Q(user=user)
            )
        return SpecialistProfile.objects.filter(is_verified=True)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != user.Roles.SPECIALIST:
            raise serializers.ValidationError(
                {"detail": "Only specialists can create a specialist profile."}
            )
        if hasattr(user, "specialist_profile"):
            raise serializers.ValidationError(
                {"detail": "You already have a specialist profile."}
            )
        serializer.save(user=user)

    def get_serializer_class(self):
        user = self.request.user
        if user.is_authenticated and user.role in ADMIN_ROLES:
            return SpecialistProfileModeratorSerializer
        return {
            "create": SpecialistProfileCreateSerializer,
            "update": SpecialistProfileUpdateSerializer,
            "partial_update": SpecialistProfileUpdateSerializer,
            "list": SpecialistProfileListSerializer,
            "retrieve": SpecialistProfileDetailSerializer,
        }.get(self.action, SpecialistProfileDetailSerializer)


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsNotBlocked]

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsNotBlocked(), IsOwnerOrStaff()]
        return [permissions.IsAuthenticated(), IsNotBlocked()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role in ADMIN_ROLES:
            return Document.objects.all()
        return Document.objects.filter(specialist__user=user)

    def get_serializer_class(self):
        user = self.request.user
        if user.is_authenticated and user.role in ADMIN_ROLES:
            return DocumentModeratorSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != user.Roles.SPECIALIST:
            raise serializers.ValidationError(
                {"detail": "Only specialists can upload documents."}
            )
        specialist = getattr(user, "specialist_profile", None)
        if specialist is None:
            raise serializers.ValidationError(
                {"detail": "You need a specialist profile to upload documents."}
            )
        serializer.save(specialist=specialist)
