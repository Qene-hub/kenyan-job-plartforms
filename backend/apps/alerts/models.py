from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.utils import KENYA_COUNTIES, ExperienceLevel, JobType, WorkMode


class JobAlert(TimeStampedModel):
    """A saved search. New matching jobs are emailed on the chosen schedule."""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_alerts"
    )
    name = models.CharField(max_length=100)
    query = models.CharField(max_length=200, blank=True)
    county = models.CharField(max_length=30, choices=KENYA_COUNTIES, blank=True)
    job_type = models.CharField(max_length=20, choices=JobType.choices, blank=True)
    work_mode = models.CharField(max_length=20, choices=WorkMode.choices, blank=True)
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices, blank=True)
    skills = models.JSONField(default=list, blank=True)
    min_salary = models.PositiveIntegerField(null=True, blank=True)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.DAILY)
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.name} ({self.user})"