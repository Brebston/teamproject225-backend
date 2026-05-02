from django.urls import include, path
from rest_framework.routers import DefaultRouter

from events.api.v1.views import EventViewSet, CommentViewSet, CategoryViewSet

app_name = "events"

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="event-category")
router.register("comments", CommentViewSet, basename="event-comment")
router.register("", EventViewSet, basename="event")


urlpatterns = [
    path("", include(router.urls)),
]
