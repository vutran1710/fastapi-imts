from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from libs import (create_auth_response, crypt, jwt_guard, validate_google_user,
                  validate_password)
from model.auth import AuthenticatedUser, FBLoginData, GoogleLoginData
from model.http import AuthResponse, FBUserInfo
from repository import Http, PgRepo, get_http, get_pg

router = APIRouter()


@router.post("/google", response_model=AuthResponse)
async def auth_with_google(
    payload: GoogleLoginData,
    pg: PgRepo = Depends(get_pg),
):
    pwd_valid = validate_google_user(payload.id_token, payload.email)
    email, id_token, expire_at = payload.email, payload.id_token, payload.expire_at

    if not pwd_valid:
        raise HTTPException(400)

    await pg.insert_user_if_needed(email, id_token, expire_at, "google")

    resp = create_auth_response(email, "google")
    return resp


@router.post("/facebook", response_model=AuthResponse)
async def auth_with_facebook(
    payload: FBLoginData,
    pg: PgRepo = Depends(get_pg),
    http: Http = Depends(get_http),
):
    info = await http.authenticate_facebook_user(payload)

    if not info:
        raise HTTPException(400)

    email, access_token, expire_at = info.email, payload.access_token, payload.expire_at

    await pg.insert_user_if_needed(email, access_token, expire_at, "facebook")

    resp = create_auth_response(info.name, "facebook")
    return resp


@router.post("/register", response_model=AuthResponse)
async def registration_with_username_password(
    form_data: OAuth2PasswordRequestForm = Depends(),
    pg: PgRepo = Depends(get_pg),
):
    email, password = form_data.username, form_data.password
    validate_password(password)

    success = await pg.register_new_user(email, crypt.hash(password))

    if not success:
        raise HTTPException(400, "Account already exists")

    resp = create_auth_response(email, "app")
    return resp


@router.post("/login", response_model=AuthResponse)
async def login_with_username_password(
    form_data: OAuth2PasswordRequestForm = Depends(),
    pg: PgRepo = Depends(get_pg),
):
    email, pwd = form_data.username, form_data.password
    pwd_valid = crypt.verify(pwd, await pg.retrieve_password(email))

    if not pwd_valid:
        raise HTTPException(401, "Invalid username or password")

    resp = create_auth_response(email, "app")
    return resp


@router.post("/access-token", response_model=AuthResponse)
async def get_access_token(
    user: AuthenticatedUser = Depends(jwt_guard),
    pg: PgRepo = Depends(get_pg),
):
    if user.provider != "app":
        found_token = await pg.retrieve_user_token(user.email)

        if not found_token:
            raise HTTPException(401, "Invalid credential data")

    resp = create_auth_response(user.email, user.provider)
    return resp


@router.get("/refresh-token", response_model=AuthResponse)
async def refresh_token(
    user: AuthenticatedUser = Depends(jwt_guard),
    pg: PgRepo = Depends(get_pg),
):
    if user.provider != "app":
        social_token = await pg.retrieve_user_token(user.email)

        if not social_token:
            raise HTTPException(400, "User's social token is invalid")

    resp = create_auth_response(user.email, user.provider)
    return resp


@router.get("/logout")
async def logout(
    user: AuthenticatedUser = Depends(jwt_guard),
    pg: PgRepo = Depends(get_pg),
):
    if user.provider != "app":
        await pg.remove_user_token(user.email)

    return "Logged out"
