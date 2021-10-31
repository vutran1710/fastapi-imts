"""Testing authentication flow of App
"""
from model.http import AuthResponse

from .fixtures import API, pytestmark, setup  # noqa


async def test_sign_up_and_login(setup):  # noqa
    """Testing
    - Sign-up
    - Login
    - Refresh Token
    - Social-login is not tested for now
    """
    client, pg, _ = setup

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
