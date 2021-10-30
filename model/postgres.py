from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from .enums import Provider


class User(BaseModel):
    id: UUID
    email: EmailStr
    password: Optional[str]
    token: Optional[str]
    expire_at: Optional[datetime]
    created_at: datetime
    provider: Provider


class Image(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    storage_key: str
    uploaded_by: Optional[UUID]


class Tag(BaseModel):
    id: int
    name: str


class TaggedImage(BaseModel):
    image: Image
    tags: List[Tag]
