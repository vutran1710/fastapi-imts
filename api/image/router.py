from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from dependencies import auth_guard, get_minio, get_pg
from libs import (ImageException, fix_tags, make_storage_key,
                  validate_image_file)
from model.auth import AuthenticatedUser
from model.http import FindImageResponse, UploadImageResponse
from model.postgres import Image, TaggedImage
from repository import Minio, Postgres


async def find_image_by_id(pg: Postgres, minio: Minio, image_id: UUID):
    image = await pg.get_image(image_id)

    if not image:
        raise ImageException.INVALID_IMAGE_ID

    tags = await pg.get_image_tags(image.id)
    url = minio.get_image(image.storage_key)

    return FindImageResponse(**image.dict(), url=url, tags=tags)


async def find_images_by_tags_datetime(
    tags: List[str],
    from_date: date,
    to_date: date,
    limit: int,
    offset: int,
    pg: Postgres,
    minio: Minio,
) -> List[FindImageResponse]:
    images = await pg.search_image_by_tags(
        tags,
        limit=limit,
        offset=offset,
        from_date=from_date,
        to_date=to_date,
    )

    result = []

    for img in images:
        url = minio.get_image(img.image.storage_key)
        tag_names = [t.name for t in img.tags]
        resp = FindImageResponse(**img.image.dict(), url=url, tags=tag_names)
        result.append(resp)

    return result


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
    Upload Image
    - Maximum file size guard shall be handled by web-server ie  nginx or traefik
    """
    valid = validate_image_file(image.filename)

    if not valid:
        raise ImageException.IMAGE_ONLY

    storage_key = make_storage_key(image.filename)
    minio.save_image(storage_key, image.file)

    fixed_tags = fix_tags(tags)

    if not fix_tags:
        saved_image: Image = await pg.save_image(
            image.filename, storage_key, user.user_id
        )
        return UploadImageResponse(
            id=saved_image.id,
            name=image.filename,
            uploaded_by=saved_image.uploaded_by,
            created_at=saved_image.created_at,
        )

    tagged_image: TaggedImage = await pg.save_tagged_image(
        image.filename, storage_key, user.user_id, fixed_tags
    )
    return UploadImageResponse(
        id=tagged_image.image.id,
        name=image.filename,
        uploaded_by=tagged_image.image.uploaded_by,
        created_at=tagged_image.image.created_at,
        tags=fixed_tags,
    )


@router.get("/find", response_model=List[FindImageResponse])
async def find_images(
    image_id: Optional[UUID] = None,
    tags: Optional[str] = None,
    from_date: date = datetime.fromtimestamp(0).date(),
    to_date: date = datetime.now().date(),
    limit: int = 5,
    offset: int = 0,
    user: AuthenticatedUser = Depends(auth_guard),
    minio: Minio = Depends(get_minio),
    pg: Postgres = Depends(get_pg),
):
    """Get single image using image-id, or
    search multiple images using tags & datetime
    """
    if image_id:
        resp = await find_image_by_id(pg, minio, image_id)
        return [resp]

    valid_tags = fix_tags(tags)

    if not valid_tags:
        return []

    resp = await find_images_by_tags_datetime(
        valid_tags, from_date, to_date, limit, offset, pg, minio
    )

    return resp
