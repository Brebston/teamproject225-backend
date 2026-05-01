from django.urls import include, path
from rest_framework.routers import DefaultRouter

from events.api.v1.views import EventViewSet, CommentViewSet

app_name = "events"

router = DefaultRouter()
router.register("", EventViewSet)
router.register("comments", CommentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
