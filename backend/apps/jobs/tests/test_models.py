from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.jobs.models import Job
from apps.jobs.tasks import expire_jobs


@pytest.mark.django_db
def test_job_gets_slug_and_published_at(make_job):
    job = make_job()

    assert job.slug.startswith("python-developer")
    assert job.published_at is not None


@pytest.mark.django_db
def test_slugs_are_unique(make_job):
    first = make_job()
    second = make_job()

    assert first.slug != second.slug


@pytest.mark.django_db
def test_salary_display(make_job):
    ranged = make_job(salary_min=50000, salary_max=80000)
    single = make_job(salary_min=30000)
    none = make_job()

    assert ranged.salary_display == "KES 50,000 – 80,000 per month"
    assert single.salary_display == "KES 30,000 per month"
    assert none.salary_display == ""


@pytest.mark.django_db
def test_duplicate_active_job_fails_validation(make_job):
    original = make_job(title="Data Analyst")
    duplicate = Job(
        company=original.company,
        title="Data  analyst!",
        description="Same role again.",
        county="nairobi",
        application_url="https://example.com/apply",
        status=Job.Status.DRAFT,
    )

    with pytest.raises(ValidationError) as excinfo:
        duplicate.full_clean()

    assert "title" in excinfo.value.message_dict


@pytest.mark.django_db
def test_clean_requires_an_application_method_and_valid_salary(company):
    job = Job(
        company=company,
        title="Accountant",
        description="Keep the books.",
        salary_min=90000,
        salary_max=10000,
    )

    with pytest.raises(ValidationError) as excinfo:
        job.full_clean()

    errors = excinfo.value.message_dict
    assert "salary_max" in errors
    assert "application_url" in errors


@pytest.mark.django_db
def test_expire_jobs_closes_only_past_deadline_jobs(make_job):
    today = timezone.localdate()
    expired = make_job(title="Old job", deadline=today - timedelta(days=1))
    current = make_job(title="Current job", deadline=today + timedelta(days=3))

    assert expire_jobs() == 1

    expired.refresh_from_db()
    current.refresh_from_db()
    assert expired.status == Job.Status.CLOSED
    assert current.status == Job.Status.PUBLISHED