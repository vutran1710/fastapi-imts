from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from .enums import Provider


class User(BaseModel):
    id: int
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
    uploaded_by: Optional[int]


class Tag(BaseModel):
    """Make default ID=-1 when we dont really care about the tag id"""

    id: int = -1
    name: str


class TaggedImage(BaseModel):
    image: Image
    tags: List[Tag]

    @property
    def tag_names(self):
        return [t.name for t in self.tags]
