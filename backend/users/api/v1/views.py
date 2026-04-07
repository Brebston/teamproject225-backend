from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from users.models import User
from users.api.v1.serializers import (
    UserSerializer,
    MeSerializer,
    RoleUpdateSerializer,
)
from users.api.v1.permissions import IsAdminOrModerator, IsNotBlocked
from users.services import block_user, change_user_role


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ["destroy", "block", "change_role"]:
            return [IsAuthenticated(), IsAdminOrModerator(), IsNotBlocked()]
        return [IsAuthenticated(), IsAdminUser()]

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        user = self.get_object()

        if request.user == user:
            return Response(
                {"error": "You cannot block yourself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        block_user(user)
        return Response({"status": "user blocked"})

    @action(detail=True, methods=["post"])
    def change_role(self, request, pk=None):
        user = self.get_object()

        if request.user == user:
            return Response(
                {"error": "You cannot change your own role"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_role = serializer.validated_data["role"]

        if request.user.role == user.Roles.MODERATOR and new_role == user.Roles.ADMIN:
            return Response(
                {"error": "Moderator cannot assign admin role"},
                status=status.HTTP_403_FORBIDDEN,
            )

        change_user_role(user, new_role)
        return Response({"status": "role updated"})
