"""Sends job alert emails. Run via `python manage.py send_alerts` on a schedule."""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from apps.jobs.filters import salary_at_least_q
from apps.jobs.models import Job

from .models import JobAlert

logger = logging.getLogger(__name__)

MAX_JOBS_PER_EMAIL = 20
PERIODS = {
    JobAlert.Frequency.DAILY: timedelta(days=1),
    JobAlert.Frequency.WEEKLY: timedelta(days=7),
}
# A cron that fires daily at the same minute must not skip a day because of a few seconds' drift.
GRACE = timedelta(hours=1)


def matching_jobs(alert, since):
    """Public jobs published after `since` that satisfy every criterion of the alert."""
    queryset = Job.objects.public().filter(published_at__gt=since)

    if alert.query:
        queryset = queryset.filter(
            Q(title__icontains=alert.query)
            | Q(company__name__icontains=alert.query)
            | Q(description__icontains=alert.query)
            | Q(skills__name__icontains=alert.query)
        )
    if alert.county:
        queryset = queryset.filter(county=alert.county)
    if alert.job_type:
        queryset = queryset.filter(job_type=alert.job_type)
    if alert.work_mode:
        queryset = queryset.filter(work_mode=alert.work_mode)
    if alert.experience_level:
        queryset = queryset.filter(experience_level=alert.experience_level)
    if alert.skills:
        skill_query = Q()
        for name in alert.skills:
            skill_query |= Q(skills__name__iexact=name)
        queryset = queryset.filter(skill_query)
    if alert.min_salary:
        queryset = queryset.filter(salary_at_least_q(alert.min_salary))

    return queryset.select_related("company").distinct().order_by("-published_at", "-id")


def _is_due(alert, now):
    if alert.last_sent_at is None:
        return True
    return now - alert.last_sent_at >= PERIODS[alert.frequency] - GRACE


def _build_email(alert, jobs, total):
    site = settings.SITE_URL.rstrip("/")
    lines = [f"Hello {alert.user.get_username()},", "", f'New jobs matching your alert "{alert.name}":', ""]
    for job in jobs:
        lines.append(f"- {job.title} at {job.company.name}")
        lines.append(f"  {site}/jobs/{job.pk}/")
    if total > len(jobs):
        lines.append("")
        lines.append(f"...and {total - len(jobs)} more. Open the website to see them all.")
    lines.append("")
    lines.append("You can pause or delete this alert from your dashboard.")
    subject = f"{total} new job{'s' if total != 1 else ''} for your alert: {alert.name}"
    return subject, "\n".join(lines)


def send_job_alerts(frequency=None):
    """Process due alerts. Returns a dict of counters."""
    now = timezone.now()
    alerts = (
        JobAlert.objects.filter(is_active=True, user__is_active=True)
        .exclude(user__email="")
        .select_related("user")
    )
    if frequency:
        alerts = alerts.filter(frequency=frequency)

    stats = {"processed": 0, "sent": 0, "no_matches": 0, "failed": 0, "not_due": 0}

    for alert in list(alerts):
        if not _is_due(alert, now):
            stats["not_due"] += 1
            continue

        stats["processed"] += 1
        since = alert.last_sent_at or alert.created_at
        queryset = matching_jobs(alert, since)
        total = queryset.count()

        if total == 0:
            stats["no_matches"] += 1
        else:
            jobs = list(queryset[:MAX_JOBS_PER_EMAIL])
            subject, body = _build_email(alert, jobs, total)
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [alert.user.email])
            except Exception:
                logger.exception("Failed to send alert %s", alert.pk)
                stats["failed"] += 1
                continue  # keep last_sent_at so the same jobs are retried next run
            stats["sent"] += 1

        alert.last_sent_at = now
        alert.save(update_fields=["last_sent_at", "updated_at"])

    return stats