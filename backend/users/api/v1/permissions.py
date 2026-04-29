from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [
            request.user.Roles.ADMIN,
            request.user.Roles.MODERATOR,
        ]


class IsNotBlocked(BasePermission):
    message = "Your account is blocked"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True

        return not request.user.is_blocked


class IsOwnerOrStaff(BasePermission):
    """Object-level: only the owner or Admin/Moderator can read & write."""

    def has_object_permission(self, request, view, obj):
        if request.user.role in [
            request.user.Roles.ADMIN,
            request.user.Roles.MODERATOR,
        ]:
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        if hasattr(obj, "specialist"):
            return obj.specialist.user == request.user

        return False
