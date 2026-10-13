"""Job listings, skills and source tracking."""
import hashlib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.companies.models import Company
from apps.core.cache import NAMESPACE_COMPANIES, NAMESPACE_JOBS, bump_version
from apps.core.models import TimeStampedModel
from apps.core.utils import (
    KENYA_COUNTIES,
    ExperienceLevel,
    JobType,
    WorkMode,
    generate_unique_slug,
    normalize_text,
)


class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True, editable=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_from_name(cls, name):
        name = " ".join(name.split())[:50]
        return cls.objects.filter(name__iexact=name).first() or cls.objects.create(name=name)


def public_job_q(prefix=""):
    """Q object for 'published and not past its deadline'.

    `prefix` lets other models reuse it through a relation, e.g. public_job_q("jobs__").
    """
    today = timezone.localdate()
    return Q(**{f"{prefix}status": Job.Status.PUBLISHED}) & (
        Q(**{f"{prefix}deadline__isnull": True}) | Q(**{f"{prefix}deadline__gte": today})
    )


class JobQuerySet(models.QuerySet):
    def public(self):
        """The ONLY definition of what visitors may see: published, unexpired, verified company."""
        return self.filter(
            public_job_q(),
            company__verification_status=Company.VerificationStatus.VERIFIED,
        )

    def expired(self):
        """Published jobs whose deadline has passed and that should be closed."""
        return self.filter(status=Job.Status.PUBLISHED, deadline__lt=timezone.localdate())


class Job(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        PUBLISHED = "published", "Published"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"

    class SalaryPeriod(models.TextChoices):
        HOURLY = "hour", "Hour"
        DAILY = "day", "Day"
        MONTHLY = "month", "Month"
        YEARLY = "year", "Year"

    # Statuses in which a job still counts for duplicate detection.
    ACTIVE_STATUSES = (Status.DRAFT, Status.PENDING_REVIEW, Status.PUBLISHED)

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True, editable=False)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name="jobs")

    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    work_mode = models.CharField(max_length=20, choices=WorkMode.choices, default=WorkMode.ON_SITE)
    experience_level = models.CharField(
        max_length=20, choices=ExperienceLevel.choices, default=ExperienceLevel.ENTRY
    )
    county = models.CharField(max_length=30, choices=KENYA_COUNTIES, blank=True)
    location_detail = models.CharField(max_length=150, blank=True)

    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="KES")
    salary_period = models.CharField(
        max_length=10, choices=SalaryPeriod.choices, default=SalaryPeriod.MONTHLY
    )

    deadline = models.DateField(null=True, blank=True)
    application_url = models.URLField(max_length=500, blank=True)
    application_email = models.EmailField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posted_jobs",
    )
    # Hash of (company, normalised title, county), used to detect duplicate listings.
    fingerprint = models.CharField(max_length=64, blank=True, editable=False, db_index=True)

    objects = JobQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "deadline"]),
            models.Index(fields=["county"]),
            models.Index(fields=["job_type"]),
            models.Index(fields=["published_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.company.name})"

    # --- Computed properties ---
    @property
    def is_expired(self):
        return self.deadline is not None and self.deadline < timezone.localdate()

    @property
    def is_public(self):
        return self.status == self.Status.PUBLISHED and not self.is_expired and self.company.is_verified

    @property
    def salary_display(self):
        low, high = self.salary_min, self.salary_max
        if low is None and high is None:
            return ""
        if low is not None and high is not None and low != high:
            amount = f"{low:,} – {high:,}"
        else:
            amount = f"{(low if low is not None else high):,}"
        return f"{self.salary_currency} {amount} per {self.get_salary_period_display().lower()}"

    # --- Duplicate detection ---
    @staticmethod
    def compute_fingerprint(company_id, title, county):
        raw = "|".join([str(company_id), normalize_text(title), county or ""])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # --- Validation and saving ---
    def clean(self):
        super().clean()
        errors = {}

        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            errors["salary_max"] = "Maximum salary cannot be lower than the minimum salary."

        if not self.application_url and not self.application_email:
            errors["application_url"] = "Provide an application URL or an application email."

        if self.company_id and self.title and self.status in self.ACTIVE_STATUSES:
            fingerprint = self.compute_fingerprint(self.company_id, self.title, self.county)
            duplicate = (
                Job.objects.filter(fingerprint=fingerprint, status__in=self.ACTIVE_STATUSES)
                .exclude(pk=self.pk)
                .exists()
            )
            if duplicate:
                errors["title"] = (
                    "A similar active job already exists for this company in this county."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.fingerprint = self.compute_fingerprint(self.company_id, self.title, self.county)
        if not self.slug:
            self.slug = generate_unique_slug(self, f"{self.title} {self.company.name}")
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class JobSource(TimeStampedModel):
    """Where a job came from, with the original URL and when it was last verified."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="sources")
    name = models.CharField(max_length=50, default="manual")  # manual, employer, adzuna, ...
    source_url = models.URLField(max_length=500, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_verified_at", "-created_at"]
        constraints = [
            # NULL external ids (manual entries) never collide in MySQL unique indexes.
            models.UniqueConstraint(fields=["name", "external_id"], name="unique_source_external_id")
        ]

    def __str__(self):
        return f"{self.name}: {self.source_url or self.external_id or 'n/a'}"


# --- Cache invalidation: any change to jobs or skills refreshes cached list responses ---


def _invalidate_public_caches():
    bump_version(NAMESPACE_JOBS)
    bump_version(NAMESPACE_COMPANIES)


@receiver([post_save, post_delete], sender=Job)
def invalidate_caches_on_job_change(sender, **kwargs):
    _invalidate_public_caches()


@receiver([post_save, post_delete], sender=Skill)
def invalidate_caches_on_skill_change(sender, **kwargs):
    bump_version(NAMESPACE_JOBS)


@receiver(m2m_changed, sender=Job.skills.through)
def invalidate_caches_on_job_skills_change(sender, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        bump_version(NAMESPACE_JOBS)