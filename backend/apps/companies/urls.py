from rest_framework.routers import SimpleRouter

from .views import CompanyViewSet

router = SimpleRouter()
router.register("companies", CompanyViewSet, basename="company")

urlpatterns = router.urls