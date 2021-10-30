"""Testing authentication flow of App
"""
import pytest
import pytest_asyncio  # noqa
from fastapi.testclient import TestClient

from main import app
from model.http import AuthResponse
from repository.postgres import Postgres
from settings import settings

client = TestClient(app)

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def setup_pg():
    """Before each test, init a new Postgres instance
    Note that since each test case has its own event-loop,
    the pg instance must be created separately
    """
    pg = await Postgres.init(settings)

    yield pg

    await pg.c.close()


async def test_sign_up_and_login(setup_pg):
    """Testing
    - Sign-up
    - Login
    - Refresh Token
    - Social-login is not tested for now
    """

    class API:
        signup = "v1/auth/sign-up"
        login = "v1/auth/login"
        refresh = "v1/auth/refresh-token"

    invalid_password = "1"
    email, password = "somemail@vutr.io", "123123123"

    # Sign-up with short password is not allowed
    response = client.post(
        API.signup,
        data={"username": email, "password": invalid_password},
    )
    assert response.status_code == 400

    # Sign-up with valid credential should succeed
    response = client.post(
        API.signup,
        data={"username": email, "password": password},
    )
    assert response.status_code == 200

    data = response.json()
    assert AuthResponse(**data)

    # Sign up again with same email is not allowed
    response = client.post(
        API.signup,
        data={"username": email, "password": password},
    )
    assert response.status_code == 400

    # Login
    response = client.post(
        API.login,
        data={"username": email, "password": password},
    )

    assert response.status_code == 200
    data = response.json()
    auth = AuthResponse(**data)
    assert auth

    # Login witn incorrect credential
    response = client.post(
        API.login,
        data={"username": email, "password": invalid_password},
    )
    assert response.status_code == 400

    response = client.post(
        API.login,
        data={"username": "non-exist@mail.com", "password": invalid_password},
    )
    assert response.status_code == 400

    # Exchange new token
    response = client.get(
        API.refresh,
        headers={"Authorization": f"Bearer {auth.access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    AuthResponse(**data)

    # cleanup
    await setup_pg.c.fetch("DELETE FROM users WHERE email = $1", email)
