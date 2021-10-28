from fastapi import APIRouter, Depends

from libs.dependencies import jwt_guard
from model.auth import AuthenticatedUser

router = APIRouter()


@router.get("/")
async def get_user_profile(user: AuthenticatedUser = Depends(jwt_guard)):
    return "ok"
