from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, validator

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
    user_id: UUID
    email: str
    provider: Provider


class SimpleUserCredential(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def password_requirement(cls, pwd: str):
        if len(pwd) < 8:
            raise ValueError("Password too short")
        return pwd
