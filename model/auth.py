from typing import Optional

from pydantic import BaseModel

from .enums import Provider


class GoogleLoginData(BaseModel):
    access_token: str
    id_token: str
    expire_at: int
    email: str
    name: str


class FBLoginData(BaseModel):
    access_token: str
    user_id: str
    expire_at: int


class AuthenticatedUser(BaseModel):
    name: Optional[str]
    email: str
    provider: Provider
