from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            getattr(obj, "user", None) == request.user
            or getattr(obj, "author", None) == request.user
        )
