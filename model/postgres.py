from datetime import datetime
from typing import Optional
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
