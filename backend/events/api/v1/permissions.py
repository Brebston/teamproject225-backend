from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return (
            obj.author == request.user
            or request.user.role == request.user.Roles.ADMIN
        )


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if user.is_staff:
            return True

        if user.role == user.Roles.ADMIN:
            return True

        return False


class IsSpecialistOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff:
            return True

        if user.role == user.Roles.ADMIN:
            return True

        if hasattr(user, "specialist_profile"):
            return True

        return False
