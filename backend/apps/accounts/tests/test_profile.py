import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

PROFILE_URL = "/api/v1/auth/profile/"
CV_URL = "/api/v1/auth/profile/cv/"


def test_profile_update_cleans_skills(auth_client):
    response = auth_client.patch(
        PROFILE_URL,
        {"headline": "Backend developer", "skills": ["Python", "python", " Django "], "county": "nairobi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["skills"] == ["Python", "Django"]
    assert body["has_cv"] is False
    assert "cv" not in body


def test_cv_upload_download_and_delete(auth_client):
    content = b"%PDF-1.4 sample cv"
    upload = auth_client.patch(
        PROFILE_URL,
        {"cv": SimpleUploadedFile("cv.pdf", content, content_type="application/pdf")},
        format="multipart",
    )
    assert upload.status_code == 200
    assert upload.json()["has_cv"] is True

    download = auth_client.get(CV_URL)
    assert download.status_code == 200
    assert b"".join(download.streaming_content) == content
    assert "attachment" in download["Content-Disposition"]

    assert auth_client.delete(CV_URL).status_code == 204
    assert auth_client.get(CV_URL).status_code == 404


def test_cv_rejects_disallowed_extension(auth_client):
    response = auth_client.patch(
        PROFILE_URL,
        {"cv": SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")},
        format="multipart",
    )

    assert response.status_code == 400
    assert "cv" in response.json()


def test_change_password(auth_client, user):
    wrong = auth_client.post(
        "/api/v1/auth/password/change/",
        {"old_password": "bad", "new_password": "Zebra-Mango-47!x"},
    )
    assert wrong.status_code == 400

    ok = auth_client.post(
        "/api/v1/auth/password/change/",
        {"old_password": "StrongPass!234", "new_password": "Zebra-Mango-47!x"},
    )
    assert ok.status_code == 200
    user.refresh_from_db()
    assert user.check_password("Zebra-Mango-47!x")