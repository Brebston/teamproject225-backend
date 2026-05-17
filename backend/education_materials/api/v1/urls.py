from django.urls import path, include
from rest_framework.routers import DefaultRouter

from education_materials.api.v1.views import (
    ArticleViewSet,
    ArticleCommentViewSet,
    VideoMaterialViewSet,
    VideoCommentViewSet,
)

app_name = "education-materials"


router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="articles")
router.register("article-comments", ArticleCommentViewSet, basename="comments")
router.register("videos", VideoMaterialViewSet, basename="videos")
router.register(
    "video-comments", VideoCommentViewSet, basename="video-comments"
)
urlpatterns = [
    path("", include(router.urls)),
]
