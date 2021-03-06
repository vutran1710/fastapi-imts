from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from dependencies import (auth_guard, create_auth_response, get_http, get_pg,
                          get_redis)
from libs import AuthException, Crypt, initialize_model, validate_google_user
from model.auth import (AuthenticatedUser, FBLoginData, GoogleLoginData,
                        SimpleUserCredential)
from model.http import AuthResponse
from repository import Http, Postgres, Redis

router = APIRouter()


@router.post("/sign-up", response_model=AuthResponse)
async def sign_up_with_username_password(
    form_data: OAuth2PasswordRequestForm = Depends(),
    pg: Postgres = Depends(get_pg),
):
    email, password = form_data.username, form_data.password
    cred = initialize_model(SimpleUserCredential, email=email, password=password)

    if not cred:
        raise AuthException.INVALID_CREDENTIAL

    user = await pg.save_user(cred.email, Crypt.hash(cred.password))

    if not user:
        raise AuthException.DUPLICATE_USER

    return create_auth_response(user)


@router.post("/login", response_model=AuthResponse)
async def login_with_username_password(
    form_data: OAuth2PasswordRequestForm = Depends(),
    pg: Postgres = Depends(get_pg),
):
    email, pwd = form_data.username, form_data.password
    user = await pg.get_user(email=email)

    if not user:
        raise AuthException.INVALID_EMAIL_PWD

    valid_pwd = Crypt.verify(pwd, user.password)

    if not valid_pwd:
        raise AuthException.INVALID_EMAIL_PWD

    return create_auth_response(user)


@router.get("/refresh-token", response_model=AuthResponse)
async def refresh_token(
    user: AuthenticatedUser = Depends(auth_guard),
    pg: Postgres = Depends(get_pg),
):
    if user.provider != "app":
        user_info = await pg.get_user(email=user.email)

        if not user_info or not user_info.token:
            raise AuthException.INVALID_SOCIAL_TOKEN

    return create_auth_response(user)


@router.post("/google", response_model=AuthResponse)
async def auth_with_google(
    payload: GoogleLoginData,
    pg: Postgres = Depends(get_pg),
):
    valid = validate_google_user(payload.id_token, payload.email)

    if not valid:
        raise AuthException.FAIL_GOOGLE_AUTH

    user = await pg.save_social_user(
        payload.email, payload.id_token, payload.expire_at, "google"
    )

    return create_auth_response(user)


@router.post("/facebook", response_model=AuthResponse)
async def auth_with_facebook(
    payload: FBLoginData,
    pg: Postgres = Depends(get_pg),
    http: Http = Depends(get_http),
):
    info = await http.authenticate_facebook_user(payload)

    if not info:
        raise AuthException.FAIL_FACEBOOK_AUTH

    user = await pg.save_social_user(
        info.email, payload.access_token, payload.expire_at, "facebook"
    )

    return create_auth_response(user)


@router.get("/logout", response_model=str)
async def invalidate_token_and_logout(
    user: AuthenticatedUser = Depends(auth_guard),
    rd: Redis = Depends(get_redis),
):
    now = datetime.now(timezone.utc).timestamp()
    exp = user.exp.timestamp()
    delta = timedelta(seconds=exp - now)
    await rd.invalidate_token(user.token, ttl=delta)
    return "OK"
