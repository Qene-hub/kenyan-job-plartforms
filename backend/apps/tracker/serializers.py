from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.jobs.models import Job
from apps.jobs.serializers import JobListSerializer

from .models import Application, ApplicationNote, SavedJob


class PublicJobField(serializers.PrimaryKeyRelatedField):
    """Accepts a job id, but only for jobs that are currently public."""

    def get_queryset(self):
        return Job.objects.public()


class SavedJobSerializer(serializers.ModelSerializer):
    job = JobListSerializer(read_only=True)
    job_id = PublicJobField(source="job", write_only=True)

    class Meta:
        model = SavedJob
        fields = ("id", "job", "job_id", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_job_id(self, job):
        user = self.context["request"].user
        if SavedJob.objects.filter(user=user, job=job).exists():
            raise serializers.ValidationError("You have already saved this job.")
        return job


class ApplicationSerializer(serializers.ModelSerializer):
    job = JobListSerializer(read_only=True)
    job_id = PublicJobField(source="job", write_only=True)
    notes_count = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = (
            "id",
            "job",
            "job_id",
            "status",
            "applied_date",
            "follow_up_date",
            "interview_at",
            "status_updated_at",
            "notes_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status_updated_at", "created_at", "updated_at")

    @extend_schema_field(OpenApiTypes.INT)
    def get_notes_count(self, obj):
        count = getattr(obj, "notes_count", None)
        return obj.notes.count() if count is None else count

    def validate_job_id(self, job):
        user = self.context["request"].user
        if Application.objects.filter(user=user, job=job).exists():
            raise serializers.ValidationError("You are already tracking an application for this job.")
        return job

    def update(self, instance, validated_data):
        validated_data.pop("job", None)  # the job of an existing application never changes
        new_status = validated_data.get("status")
        if new_status and new_status != instance.status:
            validated_data["status_updated_at"] = timezone.now()
        return super().update(instance, validated_data)


class ApplicationNoteSerializer(serializers.ModelSerializer):
    body = serializers.CharField(max_length=5000)

    class Meta:
        model = ApplicationNote
        fields = ("id", "body", "created_at")
        read_only_fields = ("id", "created_at")