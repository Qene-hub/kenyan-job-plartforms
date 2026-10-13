from datetime import timedelta

import pytest
from django.utils import timezone

from apps.companies.models import Company
from apps.jobs.models import Job, Skill

JOBS_URL = "/api/v1/jobs/"


def titles(response):
    return [job["title"] for job in response.json()["results"]]


@pytest.mark.django_db
def test_only_public_jobs_are_listed(api_client, make_job):
    make_job(title="Visible job")
    make_job(title="Draft job", status=Job.Status.DRAFT)
    make_job(title="Closed job", status=Job.Status.CLOSED)
    make_job(title="Expired job", deadline=timezone.localdate() - timedelta(days=1))
    pending = Company.objects.create(
        name="Pending Co", verification_status=Company.VerificationStatus.PENDING
    )
    make_job(title="Unverified company job", company=pending)

    response = api_client.get(JOBS_URL)

    assert response.status_code == 200
    assert titles(response) == ["Visible job"]


@pytest.mark.django_db
def test_job_detail_is_public_but_drafts_are_hidden(api_client, make_job):
    visible = make_job(title="Visible job")
    draft = make_job(title="Draft job", status=Job.Status.DRAFT)

    detail = api_client.get(f"{JOBS_URL}{visible.pk}/")
    assert detail.status_code == 200
    assert {"description", "application_url", "sources"} <= set(detail.json())
    assert api_client.get(f"{JOBS_URL}{draft.pk}/").status_code == 404


@pytest.mark.django_db
def test_search_matches_title_company_and_skill(api_client, make_job):
    job = make_job(title="Backend Engineer")
    job.skills.add(Skill.objects.create(name="Django"))
    make_job(title="Accountant")

    assert titles(api_client.get(JOBS_URL, {"search": "backend"})) == ["Backend Engineer"]
    assert titles(api_client.get(JOBS_URL, {"search": "django"})) == ["Backend Engineer"]
    assert len(titles(api_client.get(JOBS_URL, {"search": "acme"}))) == 2


@pytest.mark.django_db
def test_filters(api_client, make_job):
    make_job(title="Nairobi intern", county="nairobi", job_type="internship")
    make_job(
        title="Mombasa dev",
        county="mombasa",
        work_mode="remote",
        salary_min=50000,
        salary_max=80000,
    )
    make_job(title="Cheap job", county="kisumu", salary_min=20000, salary_max=30000)

    assert titles(api_client.get(JOBS_URL, {"county": "mombasa"})) == ["Mombasa dev"]
    assert titles(api_client.get(JOBS_URL, {"job_type": "internship"})) == ["Nairobi intern"]
    assert titles(api_client.get(JOBS_URL, {"work_mode": "remote"})) == ["Mombasa dev"]
    assert titles(api_client.get(JOBS_URL, {"min_salary": 60000})) == ["Mombasa dev"]
    assert len(titles(api_client.get(JOBS_URL, {"has_salary": "true"}))) == 2


@pytest.mark.django_db
def test_skills_filter_matches_any_listed_skill(api_client, make_job):
    python_job = make_job(title="Python job")
    python_job.skills.add(Skill.objects.create(name="Python"))
    make_job(title="No skills job")

    response = api_client.get(JOBS_URL, {"skills": "python,golang"})

    assert titles(response) == ["Python job"]


@pytest.mark.django_db
def test_invalid_filter_value_returns_400(api_client):
    assert api_client.get(JOBS_URL, {"county": "atlantis"}).status_code == 400


@pytest.mark.django_db
def test_pagination(api_client, make_job):
    for index in range(3):
        make_job(title=f"Job {index}")

    body = api_client.get(JOBS_URL, {"page_size": 2}).json()

    assert body["count"] == 3
    assert len(body["results"]) == 2
    assert body["next"] is not None


@pytest.mark.django_db
def test_list_cache_is_refreshed_when_jobs_change(api_client, make_job):
    make_job(title="First job")
    assert len(titles(api_client.get(JOBS_URL))) == 1

    make_job(title="Second job")

    assert len(titles(api_client.get(JOBS_URL))) == 2


@pytest.mark.django_db
def test_meta_endpoint_lists_choices(api_client):
    body = api_client.get("/api/v1/meta/").json()

    assert len(body["counties"]) == 47
    assert {"value": "internship", "label": "Internship"} in body["job_types"]