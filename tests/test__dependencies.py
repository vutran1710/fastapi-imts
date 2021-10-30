"""Unit testing FastAPI custom dependencies
"""
from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio  # noqa
from fastapi import HTTPException

from libs.dependencies import create_auth_response, jwt_guard
from model.auth import AuthenticatedUser
from model.http import AuthResponse
from model.postgres import User

pytestmark = pytest.mark.asyncio


def test_jwt_guard_and_auth_response():
    """JwtGuard shall handle user'token verification"""
    standard_user = User(
        id=uuid4(),
        email="myemail@vutr.io",
        password="powerful-password",
        created_at=datetime.now(),
        provider="app",
    )

    auth_data = create_auth_response(standard_user)

    assert isinstance(auth_data, AuthResponse)
    assert auth_data.access_token
    assert auth_data.expire_at and isinstance(auth_data.expire_at, int)
    assert auth_data.token_type == "bearer"
    assert auth_data.provider == "app"
    assert auth_data.user_id == str(standard_user.id)

    verified_user = jwt_guard(auth_data.access_token)
    assert isinstance(verified_user, AuthenticatedUser)
    assert verified_user.user_id == auth_data.user_id
    assert verified_user.email == auth_data.email
    assert verified_user.provider == auth_data.provider

    # AuthResponse can me created with AuthenticatedUser passed as param
    auth_data = create_auth_response(verified_user)
    assert isinstance(auth_data, AuthResponse)
    assert auth_data.access_token
    assert auth_data.expire_at and isinstance(auth_data.expire_at, int)
    assert auth_data.token_type == "bearer"
    assert auth_data.provider == "app"
    assert auth_data.user_id == str(standard_user.id)

    # Invalid token handling
    token = "invalid"

    try:
        jwt_guard(token)
        assert False
    except HTTPException as e:
        assert e.status_code == 401
    except Exception:
        assert False
