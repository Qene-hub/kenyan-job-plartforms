import pytest
from django.utils import timezone

from apps.jobs.models import Job
from apps.tracker.models import Application

SAVED_URL = "/api/v1/saved-jobs/"
APPLICATIONS_URL = "/api/v1/applications/"


def test_tracker_requires_authentication(api_client):
    assert api_client.get(SAVED_URL).status_code == 401
    assert api_client.get(APPLICATIONS_URL).status_code == 401


@pytest.mark.django_db
def test_save_job_and_prevent_duplicates(auth_client, make_job):
    job = make_job()

    created = auth_client.post(SAVED_URL, {"job_id": job.pk})
    assert created.status_code == 201
    assert created.json()["job"]["id"] == job.pk

    assert auth_client.post(SAVED_URL, {"job_id": job.pk}).status_code == 400
    assert auth_client.get(SAVED_URL).json()["count"] == 1

    saved_id = created.json()["id"]
    assert auth_client.delete(f"{SAVED_URL}{saved_id}/").status_code == 204
    assert auth_client.get(SAVED_URL).json()["count"] == 0


@pytest.mark.django_db
def test_cannot_save_a_job_that_is_not_public(auth_client, make_job):
    draft = make_job(status=Job.Status.DRAFT)

    assert auth_client.post(SAVED_URL, {"job_id": draft.pk}).status_code == 400


@pytest.mark.django_db
def test_application_lifecycle(auth_client, make_job):
    job = make_job()

    created = auth_client.post(APPLICATIONS_URL, {"job_id": job.pk})
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "applied"
    assert body["applied_date"] == timezone.localdate().isoformat()

    assert auth_client.post(APPLICATIONS_URL, {"job_id": job.pk}).status_code == 400

    patched = auth_client.patch(f"{APPLICATIONS_URL}{body['id']}/", {"status": "interview"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "interview"

    summary = auth_client.get(f"{APPLICATIONS_URL}summary/").json()
    assert summary["total"] == 1
    assert summary["by_status"]["interview"] == 1
    assert summary["by_status"]["applied"] == 0


@pytest.mark.django_db
def test_users_cannot_access_each_others_applications(auth_client, other_user, make_job):
    application = Application.objects.create(user=other_user, job=make_job())

    assert auth_client.get(APPLICATIONS_URL).json()["count"] == 0
    assert auth_client.get(f"{APPLICATIONS_URL}{application.pk}/").status_code == 404
    assert (
        auth_client.patch(f"{APPLICATIONS_URL}{application.pk}/", {"status": "offer"}).status_code
        == 404
    )
    assert auth_client.delete(f"{APPLICATIONS_URL}{application.pk}/").status_code == 404


@pytest.mark.django_db
def test_application_notes(auth_client, make_job):
    application_id = auth_client.post(APPLICATIONS_URL, {"job_id": make_job().pk}).json()["id"]
    notes_url = f"{APPLICATIONS_URL}{application_id}/notes/"

    created = auth_client.post(notes_url, {"body": "Prepare portfolio"})
    assert created.status_code == 201
    assert auth_client.post(notes_url, {"body": ""}).status_code == 400

    listing = auth_client.get(notes_url).json()
    assert [note["body"] for note in listing] == ["Prepare portfolio"]

    note_id = created.json()["id"]
    assert auth_client.delete(f"{notes_url}{note_id}/").status_code == 204
    assert auth_client.get(notes_url).json() == []


@pytest.mark.django_db
def test_notes_of_other_users_are_not_reachable(auth_client, other_user, make_job):
    application = Application.objects.create(user=other_user, job=make_job())

    response = auth_client.get(f"{APPLICATIONS_URL}{application.pk}/notes/")

    assert response.status_code == 404