from typing import List

from pydantic import BaseModel, HttpUrl


class QuestionPayload(BaseModel):
    content: str
    attachments: List[HttpUrl]


class CreateQuestionResponse(BaseModel):
    id: str
    closed: bool
    asked_by: str
    created_at: int
