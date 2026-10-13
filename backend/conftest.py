"""Shared pytest fixtures. Django imports are lazy so Django is fully set up first."""
import pytest


@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        username="amina", email="amina@example.com", password="StrongPass!234"
    )


@pytest.fixture
def other_user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        username="brian", email="brian@example.com", password="StrongPass!234"
    )


@pytest.fixture
def auth_client(user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def company(db):
    from apps.companies.models import Company

    return Company.objects.create(name="Acme Kenya Ltd", industry="Technology", county="nairobi")


@pytest.fixture
def make_job(db, company):
    from apps.jobs.models import Job

    def _make(**overrides):
        defaults = {
            "company": company,
            "title": "Python Developer",
            "description": "Build and maintain APIs.",
            "county": "nairobi",
            "application_url": "https://example.com/apply",
            "status": Job.Status.PUBLISHED,
        }
        defaults.update(overrides)
        return Job.objects.create(**defaults)

    return _make