from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSpecialistOrAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role in ["specialist", "admin", "moderator"]


class IsAuthorOrAdminOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user

        if not user or not user.is_authenticated:
            return False

        return obj.author == user or user.role in ["admin", "moderator"]
