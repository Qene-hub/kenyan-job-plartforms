import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

PAGES = [
    "web:home",
    "web:job-list",
    "web:login",
    "web:register",
    "web:dashboard",
    "web:saved-jobs",
    "web:applications",
    "web:alerts",
]


@pytest.mark.parametrize("name", PAGES)
def test_pages_render(client, name):
    response = client.get(reverse(name))

    assert response.status_code == 200
    assert b"Kenya" in response.content


def test_job_detail_page_renders(client):
    response = client.get(reverse("web:job-detail", args=[1]))

    assert response.status_code == 200
    assert b'data-job-id="1"' in response.content


def test_unknown_url_uses_custom_404_page(client):
    response = client.get("/definitely-not-a-page/")

    assert response.status_code == 404
    assert b"Page not found" in response.content