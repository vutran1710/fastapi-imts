from fastapi import APIRouter, Depends
from libs import jwt_guard
from model.auth import AuthenticatedUser
from model.question import CreateQuestionResponse, QuestionPayload
from repository import PgRepo, get_pg

router = APIRouter()


@router.post("/", response_model=CreateQuestionResponse)
async def submit_question(
    payload: QuestionPayload,
    user: AuthenticatedUser = Depends(jwt_guard),
    pg: PgRepo = Depends(get_pg),
):

    return CreateQuestionResponse(
        id="id",
        closed=False,
        created_at=1,
        asked_by=user.email,
    )
