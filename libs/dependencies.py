from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from google.auth.transport import requests
from google.oauth2 import id_token
from model.auth import AuthenticatedUser
from model.enums import Provider
from model.http import AuthResponse
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
        raise HTTPException(400)

    return AuthenticatedUser(**claim)


def create_auth_response(email: str, provider: Provider, **meta_data) -> AuthResponse:
    global jwt
    payload = {"email": email, "provider": provider, **meta_data}
    token, expire_at = jwt.encode(payload, minutes=15)
    return AuthResponse(access_token=token, expire_at=expire_at, **payload)


def validate_google_user(idtoken: str, email: str) -> bool:
    try:
        idinfo = id_token.verify_oauth2_token(
            idtoken,
            requests.Request(),
            settings.GOOGLE_APP_CLIENT_ID,
        )
        return idinfo.get("email") == email

    except ValueError:
        return False


def validate_password(pwd: str):
    if not pwd or len(pwd) < 8:
        raise HTTPException(400, "Invalid password")
