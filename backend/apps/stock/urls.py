from rest_framework.routers import DefaultRouter

from .views import BoiteViewSet, MouvementStockViewSet

router = DefaultRouter()
router.register("boites", BoiteViewSet, basename="boite")
router.register("mouvements-stock", MouvementStockViewSet, basename="mouvement-stock")

urlpatterns = router.urls
