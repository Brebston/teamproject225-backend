from django.urls import path, include
from rest_framework.routers import DefaultRouter

from education_materials.api.v1.views import (
    ArticleViewSet,
    ArticleCommentViewSet,
)

app_name = "education-materials"


router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="articles")
router.register("comments", ArticleCommentViewSet, basename="comments")
urlpatterns = [
    path("", include(router.urls)),
]
