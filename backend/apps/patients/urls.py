from rest_framework.routers import DefaultRouter

from .views import NoteMedicaleViewSet, PatientMedecinViewSet, PatientViewSet

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")
router.register("notes-medicales", NoteMedicaleViewSet, basename="note-medicale")
router.register("suivis-medecin", PatientMedecinViewSet, basename="suivi-medecin")

urlpatterns = router.urls
