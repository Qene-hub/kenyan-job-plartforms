import pytest

PASSWORD = "Zebra-Mango-47!x"


@pytest.mark.django_db
def test_full_job_seeker_flow(api_client, make_job):
    job = make_job(title="Backend Engineer")

    register = api_client.post(
        "/api/v1/auth/register/",
        {
            "username": "wanjiku",
            "email": "wanjiku@example.com",
            "password": PASSWORD,
            "password_confirm": PASSWORD,
        },
    )
    assert register.status_code == 201

    login = api_client.post("/api/v1/auth/login/", {"username": "wanjiku", "password": PASSWORD})
    assert login.status_code == 200
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")

    listing = api_client.get("/api/v1/jobs/", {"search": "backend"})
    assert listing.json()["count"] == 1

    assert api_client.post("/api/v1/saved-jobs/", {"job_id": job.pk}).status_code == 201

    application = api_client.post("/api/v1/applications/", {"job_id": job.pk})
    assert application.status_code == 201

    patched = api_client.patch(
        f"/api/v1/applications/{application.json()['id']}/", {"status": "interview"}
    )
    assert patched.status_code == 200

    alert = api_client.post("/api/v1/alerts/", {"name": "Backend roles", "query": "backend"})
    assert alert.status_code == 201

    summary = api_client.get("/api/v1/applications/summary/").json()
    assert summary["by_status"]["interview"] == 1
    assert summary["saved_jobs"] == 1