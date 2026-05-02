from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return (
            getattr(obj, "user", None) == request.user
            or getattr(obj, "author", None) == request.user
        )


class IsSpecialistOrAdmin(BasePermission):
    message = "Only specialists or admins can create events."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff:
            return True

        if hasattr(user, "specialist_profile"):
            return True

        return False
