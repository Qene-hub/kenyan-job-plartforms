import pytest

from apps.alerts.models import JobAlert
from apps.alerts.tasks import send_job_alerts

ALERTS_URL = "/api/v1/alerts/"


def test_alerts_require_authentication(api_client):
    assert api_client.get(ALERTS_URL).status_code == 401


@pytest.mark.django_db
def test_alert_requires_at_least_one_criterion(auth_client):
    response = auth_client.post(ALERTS_URL, {"name": "Empty alert"})

    assert response.status_code == 400


@pytest.mark.django_db
def test_create_update_and_isolate_alerts(auth_client, other_user):
    created = auth_client.post(
        ALERTS_URL, {"name": "Python in Nairobi", "query": "python", "county": "nairobi"}
    )
    assert created.status_code == 201
    alert_id = created.json()["id"]

    patched = auth_client.patch(f"{ALERTS_URL}{alert_id}/", {"frequency": "weekly"})
    assert patched.status_code == 200
    assert patched.json()["frequency"] == "weekly"

    foreign = JobAlert.objects.create(user=other_user, name="Theirs", query="java")
    assert auth_client.get(f"{ALERTS_URL}{foreign.pk}/").status_code == 404
    assert auth_client.get(ALERTS_URL).json()["count"] == 1


@pytest.mark.django_db
def test_alert_limit_per_user(auth_client, settings):
    settings.MAX_ALERTS_PER_USER = 1
    assert auth_client.post(ALERTS_URL, {"name": "One", "query": "python"}).status_code == 201
    assert auth_client.post(ALERTS_URL, {"name": "Two", "query": "java"}).status_code == 400


@pytest.mark.django_db
def test_send_alerts_emails_only_matching_new_jobs(user, make_job, mailoutbox):
    alert = JobAlert.objects.create(user=user, name="Python", query="python", county="nairobi")
    make_job(title="Senior Python Engineer", county="nairobi")
    make_job(title="Accountant", county="mombasa")

    stats = send_job_alerts()

    assert stats["sent"] == 1
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["amina@example.com"]
    assert "Senior Python Engineer" in mailoutbox[0].body
    assert "Accountant" not in mailoutbox[0].body

    alert.refresh_from_db()
    assert alert.last_sent_at is not None
    # Not due again until the next period.
    assert send_job_alerts()["not_due"] == 1
    assert len(mailoutbox) == 1


@pytest.mark.django_db
def test_send_alerts_skips_paused_alerts(user, make_job, mailoutbox):
    JobAlert.objects.create(user=user, name="Paused", query="python", is_active=False)
    make_job(title="Python Engineer")

    stats = send_job_alerts()

    assert stats["processed"] == 0
    assert mailoutbox == []