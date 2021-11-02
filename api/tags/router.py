from fastapi import APIRouter, Depends

from libs.dependencies import auth_guard
from libs.exceptions import TagException
from model.auth import AuthenticatedUser
from model.http import AddTagsRequest, AddTagsResponse
from repository import Postgres, get_pg

router = APIRouter()


@router.post("", response_model=AddTagsResponse)
async def add_tags(
    payload: AddTagsRequest,
    pg: Postgres = Depends(get_pg),
    _: AuthenticatedUser = Depends(auth_guard),
):
    if not payload.tags:
        raise TagException.INVALID_TAGS

    await pg.save_tags(payload.tags)
    return AddTagsResponse(tags=payload.tags)
