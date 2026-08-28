from rest_framework.routers import DefaultRouter

from .views import HoraireProgrammeViewSet, PrescriptionViewSet, PriseViewSet

router = DefaultRouter()
router.register("prescriptions", PrescriptionViewSet, basename="prescription")
router.register("horaires-programmes", HoraireProgrammeViewSet, basename="horaire-programme")
router.register("prises", PriseViewSet, basename="prise")

urlpatterns = router.urls
