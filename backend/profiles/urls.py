from rest_framework.routers import DefaultRouter
from .views import ProfileViewSet, SpecialistProfileViewSet, DocumentViewSet

router = DefaultRouter()
router.register("user-profiles", ProfileViewSet, basename="profile")
router.register("specialist-profiles", SpecialistProfileViewSet, basename="specialist-profile")
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = router.urls
