from rest_framework.permissions import BasePermission


class IsAdminOrModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ["admin", "moderator"]
