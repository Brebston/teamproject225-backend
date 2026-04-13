from django.db import models
from rest_framework import generics, permissions, serializers
from users.api.v1.permissions import IsNotBlocked, IsOwner, IsAdminOrModerator
from .models import Profile, SpecialistProfile, Document
from .serializers import (
    ProfileSerializer,
    SpecialistProfileSerializer,
    DocumentSerializer,
    DocumentModeratorSerializer,
)


class ProfileListCreateView(generics.ListCreateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotBlocked]

    def get_queryset(self):
        # Everyone can browse profiles now
        return Profile.objects.all()

    def perform_create(self, serializer):
        if hasattr(self.request.user, "profile"):
            raise serializers.ValidationError(
                {"detail": "You already have a profile."}
            )
        serializer.save(user=self.request.user)


class ProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotBlocked, IsOwner]


class SpecialistProfileListCreateView(generics.ListCreateAPIView):
    serializer_class = SpecialistProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotBlocked]

    def get_queryset(self):
        # Only show verified specialist profiles publicly;
        # owner can always see their own
        user = self.request.user
        return SpecialistProfile.objects.filter(
            models.Q(is_verified=True) | models.Q(user=user)
        )

    def perform_create(self, serializer):
        if not self.request.user.role == self.request.user.Roles.SPECIALIST:
            raise serializers.ValidationError(
                {"detail": "Only specialists can create a specialist profile."}
            )
        if hasattr(self.request.user, "specialist_profile"):
            raise serializers.ValidationError(
                {"detail": "You already have a specialist profile."}
            )
        serializer.save(user=self.request.user)


class SpecialistProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SpecialistProfile.objects.all()
    serializer_class = SpecialistProfileSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBlocked,
        IsOwner,
        IsAdminOrModerator,
    ]


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotBlocked]

    def get_queryset(self):
        user = self.request.user
        if IsAdminOrModerator().has_permission(self.request, self):
            return Document.objects.all()
        # Specialists only see their own documents
        return Document.objects.filter(specialist__user=user)

    def perform_create(self, serializer):
        specialist = getattr(self.request.user, "specialist_profile", None)
        if specialist is None:
            raise serializers.ValidationError(
                {
                    "detail": "You need a specialist profile to upload documents."
                }
            )
        serializer.save(specialist=specialist)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBlocked,
        IsOwner,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        user = self.request.user
        if IsAdminOrModerator().has_permission(self.request, self):
            return Document.objects.all()
        return Document.objects.filter(specialist__user=user)

    def get_serializer_class(self):
        if IsAdminOrModerator().has_permission(self.request, self):
            return DocumentModeratorSerializer
        return DocumentSerializer
