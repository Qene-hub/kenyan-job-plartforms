from rest_framework import serializers

from apps.companies.serializers import CompanyBriefSerializer

from .models import Job, JobSource, Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "name", "slug")
        read_only_fields = fields


class JobSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSource
        fields = ("name", "source_url", "last_verified_at")
        read_only_fields = fields


class JobListSerializer(serializers.ModelSerializer):
    company = CompanyBriefSerializer(read_only=True)
    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    county_display = serializers.CharField(source="get_county_display", read_only=True)
    job_type_display = serializers.CharField(source="get_job_type_display", read_only=True)
    work_mode_display = serializers.CharField(source="get_work_mode_display", read_only=True)
    experience_level_display = serializers.CharField(
        source="get_experience_level_display", read_only=True
    )
    salary_display = serializers.CharField(read_only=True)

    class Meta:
        model = Job
        fields = (
            "id",
            "slug",
            "title",
            "company",
            "county",
            "county_display",
            "location_detail",
            "job_type",
            "job_type_display",
            "work_mode",
            "work_mode_display",
            "experience_level",
            "experience_level_display",
            "salary_min",
            "salary_max",
            "salary_currency",
            "salary_period",
            "salary_display",
            "deadline",
            "published_at",
            "skills",
        )
        read_only_fields = fields


class JobDetailSerializer(JobListSerializer):
    sources = JobSourceSerializer(many=True, read_only=True)

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + (
            "description",
            "requirements",
            "application_url",
            "application_email",
            "sources",
            "updated_at",
        )
        read_only_fields = fields