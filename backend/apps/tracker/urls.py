from rest_framework.routers import SimpleRouter

from .views import ApplicationViewSet, SavedJobViewSet

router = SimpleRouter()
router.register("saved-jobs", SavedJobViewSet, basename="saved-job")
router.register("applications", ApplicationViewSet, basename="application")

urlpatterns = router.urls