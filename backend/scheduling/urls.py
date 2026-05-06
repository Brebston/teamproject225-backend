from rest_framework.routers import DefaultRouter
from .views import AvailabilitySlotViewSet, AppointmentViewSet

router = DefaultRouter()
router.register("slots",        AvailabilitySlotViewSet, basename="slot")
router.register("appointments", AppointmentViewSet,      basename="appointment")

urlpatterns = router.urls
