from datetime import datetime
from typing import List, Optional
from uuid import UUID

from libs import fix_tags
from pydantic import AnyHttpUrl, BaseModel

from .enums import Provider
from .postgres import TaggedImage


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
    user_id: int
    email: str
    provider: Provider
    access_token: str
    expire_at: int
    token_type = "bearer"


class UploadImageResponse(BaseModel):
    id: UUID
    name: str
    uploaded_by: Optional[int]
    created_at: datetime
    tags: List[str] = []


class QueryImageResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    uploaded_by: Optional[int]
    url: AnyHttpUrl
    tags: List[str] = []

    @classmethod
    def from_tagged_image(cls, img: TaggedImage):
        return cls(**img.image.dict(), tags=img.tag_names)


class SearchImagesResponse(BaseModel):
    data: List[QueryImageResponse]
    next: str = ""


class AddTagsRequest(BaseModel):
    tags: List[str]

    def __init__(self, *args, **kwargs):
        "Remove duplicate value, remove invalid tags"
        super().__init__(*args, **kwargs)
        self.tags = fix_tags(self.tags)


class AddTagsResponse(BaseModel):
    tags: List[str]
