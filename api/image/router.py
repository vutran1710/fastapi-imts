from datetime import datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from dependencies import auth_guard, get_minio, get_pg
from libs import (ImageException, fix_tags, make_storage_key,
                  validate_image_file)
from model.auth import AuthenticatedUser
from model.http import (QueryImageResponse, SearchImagesResponse,
                        UploadImageResponse)
from repository import Minio, Postgres

router = APIRouter()


@router.post("", response_model=UploadImageResponse)
async def upload_image(
    user: AuthenticatedUser = Depends(auth_guard),
    image: UploadFile = File(...),
    tags: str = Form(None),
    minio: Minio = Depends(get_minio),
    pg: Postgres = Depends(get_pg),
):
    """
    - Maximum file size guard shall be handled by web-server ie  nginx or traefik
    """
    valid = validate_image_file(image.filename)

    if not valid:
        raise ImageException.IMAGE_ONLY

    storage_key = make_storage_key(image.filename)
    minio.save_image(storage_key, image.file)

    fixed_tags = fix_tags(tags)

    tagged_image = await pg.save_tagged_image(
        image.filename, storage_key, user.user_id, fixed_tags
    )

    return UploadImageResponse(**tagged_image.image.dict(), tags=fixed_tags)


@router.get("/find_one", response_model=QueryImageResponse)
async def find_one_image(
    id: UUID,
    user: AuthenticatedUser = Depends(auth_guard),
    minio: Minio = Depends(get_minio),
    pg: Postgres = Depends(get_pg),
):
    image = await pg.get_image(id)

    if not image:
        raise ImageException.IMAGE_NOT_FOUND

    url = minio.get_image(image.image.storage_key)
    return QueryImageResponse(**image.image.dict(), tags=image.tag_names, url=url)


@router.get("/find_many", response_model=SearchImagesResponse)
async def find_images(
    tags: str,
    limit: int = 5,
    from_date: datetime = datetime.fromtimestamp(0),
    to_date: datetime = datetime.now() + timedelta(minutes=1),
    prev_id: UUID = None,
    user: AuthenticatedUser = Depends(auth_guard),
    minio: Minio = Depends(get_minio),
    pg: Postgres = Depends(get_pg),
):
    fixed_tags = fix_tags(tags)

    if not fixed_tags:
        return []

    images = await pg.search_image_by_tags(
        fixed_tags,
        limit + 1,
        from_date=from_date,
        to_date=to_date,
        previous_id=prev_id,
    )

    has_next = len(images) == limit + 1
    images = images[:-1] if has_next else images

    data = []

    for i in images:
        img_tags = i.tag_names
        img_info = i.image.dict()
        url = minio.get_image(i.image.storage_key)
        image = QueryImageResponse(**img_info, tags=img_tags, url=url)
        data.append(image)

    if not has_next:
        return SearchImagesResponse(data=data)

    to_date, prev_id = data[-1].created_at, data[-1].id

    next_params = {
        "tags": ",".join(fixed_tags),
        "limit": limit,
        "from_date": from_date,
        "to_date": to_date,
        "prev_id": prev_id,
    }

    next_link = urlencode(next_params)
    return SearchImagesResponse(data=data, next=next_link)
