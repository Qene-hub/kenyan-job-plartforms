import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint_reports_all_services_up():
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    assert body["cache"] == "up"