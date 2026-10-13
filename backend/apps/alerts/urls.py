from rest_framework.routers import SimpleRouter

from .views import JobAlertViewSet

router = SimpleRouter()
router.register("alerts", JobAlertViewSet, basename="alert")

urlpatterns = router.urls