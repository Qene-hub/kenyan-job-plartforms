from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.cache import NAMESPACE_COMPANIES, NAMESPACE_JOBS, bump_version
from apps.core.models import TimeStampedModel
from apps.core.utils import KENYA_COUNTIES, generate_unique_slug


class Company(TimeStampedModel):
    """An employer. Only verified companies appear in the public API."""

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True, editable=False)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=30, choices=KENYA_COUNTIES, blank=True)
    # Companies created by an admin are trusted by default. Imported or self-registered
    # companies are explicitly created as PENDING until reviewed.
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.VERIFIED,
    )
    # Employer account that manages this company (used by employer self-service).
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="companies",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)


@receiver([post_save, post_delete], sender=Company)
def invalidate_caches_on_company_change(sender, **kwargs):
    bump_version(NAMESPACE_JOBS)
    bump_version(NAMESPACE_COMPANIES)