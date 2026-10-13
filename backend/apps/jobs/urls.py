from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import JobMetaView, JobViewSet, SkillViewSet

router = SimpleRouter()
router.register("jobs", JobViewSet, basename="job")
router.register("skills", SkillViewSet, basename="skill")

urlpatterns = [path("meta/", JobMetaView.as_view(), name="meta")] + router.urls