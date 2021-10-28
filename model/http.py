from typing import Optional

from pydantic import BaseModel

from .enums import Provider


class FBUserPicture(BaseModel):
    height: int
    width: int
    is_silhouette: bool
    url: str


class FBUserInfo(BaseModel):
    id: str
    email: str
    name: str
    picture: FBUserPicture

    def __init__(self, **kwargs):
        pic_data = kwargs.get("picture", {})

        if "data" in pic_data:
            pic_data = pic_data["data"]

        picture = FBUserPicture(**pic_data)
        info = {k: v for k, v in kwargs.items() if k in ("id", "email", "name")}
        super().__init__(picture=picture, **info)


class AuthResponse(BaseModel):
    user_id: str
    email: str
    provider: Provider
    access_token: str
    expire_at: int
    token_type = "bearer"
