from typing import Union

from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from model.auth import AuthenticatedUser
from model.http import AuthResponse
from model.postgres import User
from passlib.context import CryptContext
from settings import settings

from .jwt import Jwt

crypt = CryptContext(
    schemes=["pbkdf2_sha256"],
    default="pbkdf2_sha256",
    pbkdf2_sha256__default_rounds=30000,
)
jwt = Jwt(settings)
scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


async def jwt_guard(token: str = Depends(scheme)):
    global jwt

    claim = jwt.decode(token)

    if not claim:
        raise HTTPException(401)

    return AuthenticatedUser(**claim)


def create_auth_response(user: Union[User, AuthenticatedUser]) -> AuthResponse:
    global jwt
    user_id = None

    if isinstance(user, User):
        user_id = str(user.id)

    if isinstance(user, AuthenticatedUser):
        user_id = user.user_id

    payload = {"user_id": user_id, "email": user.email, "provider": user.provider}
    token, expire_at = jwt.encode(payload, minutes=60)
    return AuthResponse(access_token=token, expire_at=expire_at, **payload)
