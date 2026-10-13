"""Turns provider results into jobs awaiting review. Imported jobs are never auto-published."""
import logging

from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.jobs.models import Job, JobSource, Skill

from .base import JobSourceProvider, NormalizedJob

logger = logging.getLogger(__name__)


def import_item(provider_name: str, item: NormalizedJob) -> str:
    """Store one job. Returns 'created' or 'duplicate'."""
    if JobSource.objects.filter(name=provider_name, external_id=item.external_id).exists():
        return "duplicate"

    title = item.title[:200]
    company_name = item.company_name[:200]

    with transaction.atomic():
        company = Company.objects.filter(name__iexact=company_name).first()
        if company is None:
            # Unknown employers must be reviewed before their jobs can become public.
            company = Company.objects.create(
                name=company_name, verification_status=Company.VerificationStatus.PENDING
            )

        fingerprint = Job.compute_fingerprint(company.pk, title, item.county)
        if Job.objects.filter(fingerprint=fingerprint, status__in=Job.ACTIVE_STATUSES).exists():
            return "duplicate"

        job = Job.objects.create(
            company=company,
            title=title,
            description=item.description,
            county=item.county,
            location_detail=item.location_detail[:150],
            job_type=item.job_type,
            salary_min=item.salary_min,
            salary_max=item.salary_max,
            salary_currency=item.salary_currency,
            salary_period=item.salary_period,
            deadline=item.deadline,
            application_url=item.application_url[:500],
            status=Job.Status.PENDING_REVIEW,
        )
        JobSource.objects.create(
            job=job,
            name=provider_name,
            source_url=item.source_url[:500],
            external_id=item.external_id,
            last_verified_at=timezone.now(),
        )
        for skill_name in item.skills[:15]:
            if skill_name.strip():
                job.skills.add(Skill.get_or_create_from_name(skill_name))

    return "created"


def import_from_provider(provider: JobSourceProvider, query: str = "", pages: int = 1) -> dict:
    """Fetch up to `pages` pages from a provider and store the results."""
    stats = {"created": 0, "duplicates": 0, "errors": 0}

    for page in range(1, pages + 1):
        items = provider.fetch(query, page)
        if not items:
            break
        for item in items:
            try:
                outcome = import_item(provider.name, item)
            except Exception:
                logger.exception("Failed to import %s job %s", provider.name, item.external_id)
                stats["errors"] += 1
                continue
            stats["created" if outcome == "created" else "duplicates"] += 1

    return stats