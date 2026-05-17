from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from events.api.v1.views import EventViewSet, CommentViewSet, CategoryViewSet

app_name = "events"

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="event-category")
router.register("", EventViewSet, basename="event")

events_router = NestedDefaultRouter(router, "", lookup="event")
events_router.register("comments", CommentViewSet, basename="event-comment")


urlpatterns = [
    path("", include(router.urls)),
    path("", include(events_router.urls)),
]
