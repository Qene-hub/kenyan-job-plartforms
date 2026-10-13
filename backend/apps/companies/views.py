from django.db.models import Count
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.core.cache import NAMESPACE_COMPANIES, CachedListMixin
from apps.jobs.models import public_job_q

from .models import Company
from .serializers import CompanySerializer


class CompanyViewSet(CachedListMixin, viewsets.ReadOnlyModelViewSet):
    """Browse verified companies and how many open jobs each one has."""

    serializer_class = CompanySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filterset_fields = ["county", "industry"]
    search_fields = ["name", "industry", "description"]
    ordering_fields = ["name", "active_jobs_count"]
    ordering = ["name"]
    cache_namespace = NAMESPACE_COMPANIES

    def get_queryset(self):
        return Company.objects.filter(
            verification_status=Company.VerificationStatus.VERIFIED
        ).annotate(
            active_jobs_count=Count("jobs", filter=public_job_q("jobs__"), distinct=True)
        )