from django.conf import settings
from rest_framework import serializers

from apps.core.utils import clean_skill_list

from .models import JobAlert

CRITERIA = ("query", "county", "job_type", "work_mode", "experience_level", "skills", "min_salary")


class JobAlertSerializer(serializers.ModelSerializer):
    skills = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False, max_length=20
    )

    class Meta:
        model = JobAlert
        fields = (
            "id",
            "name",
            "query",
            "county",
            "job_type",
            "work_mode",
            "experience_level",
            "skills",
            "min_salary",
            "frequency",
            "is_active",
            "last_sent_at",
            "created_at",
        )
        read_only_fields = ("id", "last_sent_at", "created_at")

    def validate_skills(self, value):
        return clean_skill_list(value)

    def validate(self, attrs):
        current = {
            field: attrs.get(field, getattr(self.instance, field, None) if self.instance else None)
            for field in CRITERIA
        }
        if not any(current.values()):
            raise serializers.ValidationError(
                "Set at least one search criterion (query, county, job type, work mode, "
                "experience level, skills or minimum salary)."
            )
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        if JobAlert.objects.filter(user=user).count() >= settings.MAX_ALERTS_PER_USER:
            raise serializers.ValidationError(
                f"You can have at most {settings.MAX_ALERTS_PER_USER} alerts."
            )
        return super().create(validated_data)