from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class SavedJob(TimeStampedModel):
    """A job bookmarked by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_jobs"
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="saved_by")

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "job"], name="unique_saved_job_per_user")
        ]

    def __str__(self):
        return f"{self.user} saved {self.job_id}"


class Application(TimeStampedModel):
    """A user's application to a job, moving through the hiring pipeline."""

    class Status(models.TextChoices):
        SAVED = "saved", "Saved"
        APPLIED = "applied", "Applied"
        ASSESSMENT = "assessment", "Assessment"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    applied_date = models.DateField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    interview_at = models.DateTimeField(null=True, blank=True)
    status_updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "job"], name="unique_application_per_user_job")
        ]

    def __str__(self):
        return f"{self.user} -> {self.job_id} ({self.status})"

    def save(self, *args, **kwargs):
        if self.status == self.Status.APPLIED and self.applied_date is None:
            self.applied_date = timezone.localdate()
        super().save(*args, **kwargs)


class ApplicationNote(TimeStampedModel):
    """Private notes and interview preparation attached to an application."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="notes")
    body = models.TextField()

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Note on application {self.application_id}"