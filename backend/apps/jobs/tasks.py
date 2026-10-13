"""Scheduled maintenance for job listings (run via management commands)."""
import logging

from django.utils import timezone

from apps.core.cache import NAMESPACE_COMPANIES, NAMESPACE_JOBS, bump_version

from .models import Job

logger = logging.getLogger(__name__)


def expire_jobs():
    """Close every published job whose deadline has passed. Returns how many were closed."""
    closed = Job.objects.expired().update(status=Job.Status.CLOSED, updated_at=timezone.now())
    if closed:
        # queryset.update() does not fire signals, so refresh cached responses explicitly.
        bump_version(NAMESPACE_JOBS)
        bump_version(NAMESPACE_COMPANIES)
        logger.info("Closed %s expired job(s)", closed)
    return closed