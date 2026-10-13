import pytest

from apps.companies.models import Company
from apps.jobs.models import Job


@pytest.mark.django_db
def test_company_list_shows_only_verified_companies_with_job_counts(api_client, company, make_job):
    make_job(title="Backend Engineer")
    make_job(title="Data Analyst")
    make_job(title="Closed role", status=Job.Status.CLOSED)
    Company.objects.create(name="Hidden Co", verification_status=Company.VerificationStatus.REJECTED)

    response = api_client.get("/api/v1/companies/")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["slug"] == "acme-kenya-ltd"
    assert results[0]["active_jobs_count"] == 2


@pytest.mark.django_db
def test_company_detail_by_slug_and_unverified_is_hidden(api_client, company):
    pending = Company.objects.create(
        name="Pending Co", verification_status=Company.VerificationStatus.PENDING
    )

    assert api_client.get(f"/api/v1/companies/{company.slug}/").status_code == 200
    assert api_client.get(f"/api/v1/companies/{pending.slug}/").status_code == 404