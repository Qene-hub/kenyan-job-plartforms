import pytest

from apps.accounts.models import User

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/token/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"
PASSWORD = "Zebra-Mango-47!x"


def register_payload(**overrides):
    data = {
        "username": "njeri",
        "email": "Njeri@Example.com",
        "password": PASSWORD,
        "password_confirm": PASSWORD,
        "role": "job_seeker",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_register_creates_user_and_profile(api_client):
    response = api_client.post(REGISTER_URL, register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "njeri@example.com"
    assert "password" not in body
    assert User.objects.get(username="njeri").profile is not None


@pytest.mark.django_db
def test_register_rejects_duplicate_email_ignoring_case(api_client):
    api_client.post(REGISTER_URL, register_payload())
    response = api_client.post(
        REGISTER_URL, register_payload(username="other", email="NJERI@example.com")
    )

    assert response.status_code == 400
    assert "email" in response.json()


@pytest.mark.django_db
def test_register_rejects_mismatched_passwords(api_client):
    response = api_client.post(REGISTER_URL, register_payload(password_confirm="different"))

    assert response.status_code == 400
    assert "password_confirm" in response.json()


@pytest.mark.django_db
def test_register_rejects_weak_password(api_client):
    response = api_client.post(
        REGISTER_URL, register_payload(password="12345678", password_confirm="12345678")
    )

    assert response.status_code == 400
    assert "password" in response.json()


@pytest.mark.django_db
def test_register_cannot_create_admin_role(api_client):
    response = api_client.post(REGISTER_URL, register_payload(role="admin"))

    assert response.status_code == 400
    assert "role" in response.json()


@pytest.mark.parametrize("identifier", ["amina", "amina@example.com", "AMINA@example.com"])
def test_login_accepts_username_or_email(api_client, user, identifier):
    response = api_client.post(LOGIN_URL, {"username": identifier, "password": "StrongPass!234"})

    assert response.status_code == 200
    assert {"access", "refresh", "user"} <= set(response.json())


def test_login_rejects_wrong_password(api_client, user):
    response = api_client.post(LOGIN_URL, {"username": "amina", "password": "nope"})

    assert response.status_code == 401


def test_me_requires_authentication(api_client):
    assert api_client.get(ME_URL).status_code == 401


def test_me_returns_current_user(auth_client):
    response = auth_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["username"] == "amina"


def test_logout_blacklists_refresh_token(api_client, user):
    tokens = api_client.post(
        LOGIN_URL, {"username": "amina", "password": "StrongPass!234"}
    ).json()
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    logout = api_client.post(LOGOUT_URL, {"refresh": tokens["refresh"]})
    assert logout.status_code == 205

    api_client.credentials()
    reuse = api_client.post(REFRESH_URL, {"refresh": tokens["refresh"]})
    assert reuse.status_code == 401