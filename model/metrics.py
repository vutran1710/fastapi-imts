from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserTracking(BaseModel):
    user_id: int
    email: EmailStr
    request_url: str
    timestamp: datetime
