# backend/apps/companies/serializers.py
from rest_framework import serializers

from .models import Company


class CompanyBriefSerializer(serializers.ModelSerializer):
    """Compact company info embedded inside job listings."""

    class Meta:
        model = Company
        fields = ("id", "name", "slug", "website", "industry")
        read_only_fields = fields


class CompanySerializer(serializers.ModelSerializer):
    county_display = serializers.CharField(source="get_county_display", read_only=True)
    active_jobs_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "website",
            "industry",
            "county",
            "county_display",
            "active_jobs_count",
        )
        read_only_fields = fields