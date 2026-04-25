from rest_framework.routers import DefaultRouter

from django.urls import include, path

from users.api.v1.views import (
    LoginView,
    LogoutView,
    RegisterView,
    UserViewSet,
    GoogleLoginView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

router = DefaultRouter()
router.register("list", UserViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]
