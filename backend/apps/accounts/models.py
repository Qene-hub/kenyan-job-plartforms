# backend/apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Platform user. Job seekers and employers share one table, separated by role."""

    class Role(models.TextChoices):
        JOB_SEEKER = "job_seeker", "Job seeker"
        EMPLOYER = "employer", "Employer"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.JOB_SEEKER)

    def __str__(self):
        return self.username