from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import NAMESPACE_JOBS, CachedListMixin
from apps.core.utils import KENYA_COUNTIES, ExperienceLevel, JobType, WorkMode

from .filters import JobFilter
from .models import Job, Skill
from .serializers import JobDetailSerializer, JobListSerializer, SkillSerializer


class JobViewSet(CachedListMixin, viewsets.ReadOnlyModelViewSet):
    """Public job search. Only published, unexpired jobs from verified companies appear."""

    permission_classes = [AllowAny]
    filterset_class = JobFilter
    search_fields = ["title", "company__name", "skills__name", "description"]
    ordering_fields = ["published_at", "deadline", "salary_min", "salary_max", "title"]
    ordering = ["-published_at", "-id"]
    cache_namespace = NAMESPACE_JOBS
    cache_timeout = settings.JOB_LIST_CACHE_SECONDS

    def get_queryset(self):
        queryset = Job.objects.public().select_related("company").prefetch_related("skills")
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("sources")
        return queryset

    def get_serializer_class(self):
        return JobDetailSerializer if self.action == "retrieve" else JobListSerializer


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    """All known skills, handy for autocomplete and filters."""

    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    search_fields = ["name"]
    ordering = ["name"]


class JobMetaView(APIView):
    """Static choice lists the website needs to build its filter dropdowns."""

    permission_classes = [AllowAny]

    @extend_schema(tags=["Meta"], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        def options(choices):
            return [{"value": value, "label": str(label)} for value, label in choices]

        return Response(
            {
                "counties": options(KENYA_COUNTIES),
                "job_types": options(JobType.choices),
                "work_modes": options(WorkMode.choices),
                "experience_levels": options(ExperienceLevel.choices),
                "salary_periods": options(Job.SalaryPeriod.choices),
            }
        )