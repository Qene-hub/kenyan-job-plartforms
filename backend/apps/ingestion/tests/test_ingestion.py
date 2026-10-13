import pytest

from apps.companies.models import Company
from apps.ingestion.base import ProviderError
from apps.ingestion.importer import import_from_provider
from apps.ingestion.providers.adzuna import AdzunaProvider
from apps.jobs.models import Job

SAMPLE = {
    "results": [
        {
            "id": "123",
            "title": "Python Developer",
            "description": "Build APIs for a growing platform.",
            "redirect_url": "https://adzuna.example/job/123",
            "company": {"display_name": "Safaricom"},
            "location": {"display_name": "Westlands, Nairobi", "area": ["Kenya", "Nairobi"]},
            "salary_min": 60000.0,
            "salary_max": 90000.0,
            "salary_is_predicted": "0",
            "contract_time": "full_time",
        },
        {"id": "", "title": "Broken entry without an id"},
    ]
}


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return SAMPLE


class FakeSession:
    def get(self, url, params=None, timeout=None):
        return FakeResponse()


def make_provider():
    return AdzunaProvider(app_id="id", app_key="key", country="gb", session=FakeSession())


def test_missing_credentials_raise_provider_error(settings):
    settings.ADZUNA_APP_ID = ""
    settings.ADZUNA_APP_KEY = ""

    with pytest.raises(ProviderError):
        AdzunaProvider(country="gb")


def test_adzuna_normalizes_results_and_skips_broken_entries():
    jobs = make_provider().fetch("python")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_id == "123"
    assert job.company_name == "Safaricom"
    assert job.county == "nairobi"
    assert job.salary_min == 60000
    assert job.salary_currency == "GBP"
    assert job.job_type == "full_time"


@pytest.mark.django_db
def test_import_creates_pending_job_and_skips_duplicates():
    provider = make_provider()

    first = import_from_provider(provider, "python", pages=1)
    assert first == {"created": 1, "duplicates": 0, "errors": 0}

    job = Job.objects.get()
    assert job.status == Job.Status.PENDING_REVIEW
    assert job.company.verification_status == Company.VerificationStatus.PENDING
    assert job.sources.get().name == "adzuna"
    assert not Job.objects.public().exists()

    second = import_from_provider(provider, "python", pages=1)
    assert second == {"created": 0, "duplicates": 1, "errors": 0}
    assert Job.objects.count() == 1