from rest_framework.permissions import BasePermission


class IsAdminOrModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [
            request.user.Roles.ADMIN,
            request.user.Roles.MODERATOR,
        ]


class IsNotBlocked(BasePermission):
    def has_permission(self, request, view):
        return not getattr(request.user, "is_blocked", False)
