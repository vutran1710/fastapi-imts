from typing import Union

from fastapi import Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from model.auth import AuthenticatedUser
from model.http import AuthResponse
from model.postgres import User
from repository import MetricCollector, Redis, get_mc, get_redis
from settings import settings

from .jwt import Jwt

crypt = CryptContext(
    schemes=["pbkdf2_sha256"],
    default="pbkdf2_sha256",
    pbkdf2_sha256__default_rounds=30000,
)
jwt = Jwt(settings)
scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


async def check_token_validity(
    token: str = Depends(scheme),
    rd: Redis = Depends(get_redis),
):
    invalid = await rd.is_token_invalid(token)
    if invalid:
        raise HTTPException(401)

    return token


def jwt_guard(token: str = Depends(scheme)):
    global jwt

    claim = jwt.decode(token)

    if not claim:
        raise HTTPException(401)

    return AuthenticatedUser(**claim, token=token)


async def user_tracking(
    request: Request,
    user: AuthenticatedUser = Depends(jwt_guard),
    mc: MetricCollector = Depends(get_mc),
):
    await mc.collect_user(user, str(request.url))
    return user


async def auth_guard(
    _=Depends(check_token_validity),
    user=Depends(user_tracking),
):
    return user


def create_auth_response(user: Union[User, AuthenticatedUser]) -> AuthResponse:
    global jwt
    user_id = None

    if isinstance(user, User):
        user_id = user.id

    if isinstance(user, AuthenticatedUser):
        user_id = user.user_id

    payload = {"user_id": str(user_id), "email": user.email, "provider": user.provider}
    token, expire_at = jwt.encode(payload, minutes=60)
    return AuthResponse(access_token=token, expire_at=expire_at, **payload)
