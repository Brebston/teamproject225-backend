from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import PermissionDenied

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from dj_rest_auth.registration.views import SocialLoginView

from profiles.serializers import (
    ProfileDetailSerializer,
    SpecialistProfileDetailSerializer
)
from users.models import User
from users.api.v1.serializers import (
    RegisterSerializer,
    UserSerializer,
    MeSerializer,
    RoleUpdateSerializer,
    EmailTokenObtainSerializer,
)
from users.api.v1.permissions import IsAdminOrModerator, IsNotBlocked
from users.services import block_user, change_user_role


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ["list"]:
            return [IsAdminOrModerator(), IsNotBlocked()]
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            return [IsAdminOrModerator(), IsNotBlocked()]
        if self.action in ["block", "change_role"]:
            return [IsAuthenticated(), IsAdminOrModerator(), IsNotBlocked()]

        return [IsAuthenticated(), IsNotBlocked()]

    def get_queryset(self):
        user = self.request.user

        if user.role in [User.Roles.ADMIN, User.Roles.MODERATOR]:
            return User.objects.all()

        return User.objects.filter(id=user.id)

    @action(detail=False, methods=["get"])
    def me(self, request):
        if hasattr(request.user, "specialist_profile"):
            serializer = SpecialistProfileDetailSerializer(request.user.specialist_profile)
        elif hasattr(request.user, "profile"):
            serializer = ProfileDetailSerializer(request.user.profile)
        else:
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

        if (
            request.user.role == user.Roles.MODERATOR
            and new_role == user.Roles.ADMIN
        ):
            return Response(
                {"error": "Moderator cannot assign admin role"},
                status=status.HTTP_403_FORBIDDEN,
            )

        change_user_role(user, new_role)
        return Response({"status": "role updated"})


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainSerializer
    permission_classes = [AllowAny]


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh = request.data.get("refresh")

            if not refresh:
                return Response(
                    {"error": "Refresh token required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh)
            token.blacklist()

            return Response({"detail": "Logged out successfully"})

        except Exception:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )


class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = "http://localhost:5173/auth/google/callback"

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)

        user = self.user

        if user.is_blocked:
            raise PermissionDenied("User is blocked")

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )
