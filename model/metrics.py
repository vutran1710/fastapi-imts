from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserTracking(BaseModel):
    user_id: UUID
    email: EmailStr
    request_url: str
    timestamp: datetime
