from rest_framework.routers import DefaultRouter

from django.urls import include, path

from users.api.v1.views import UserViewSet

router = DefaultRouter()
router.register("", UserViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls))
]
