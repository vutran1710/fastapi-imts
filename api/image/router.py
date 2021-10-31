from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from libs.dependencies import jwt_guard
from libs.exceptions import ImageException
from libs.utils import fix_tags, make_storage_key, validate_image_file
from model.auth import AuthenticatedUser
from model.http import GetImageResponse, UploadImageResponse
from model.postgres import Image, TaggedImage
from repository import Minio, Postgres, get_minio, get_pg


async def find_image_by_id(pg: Postgres, minio: Minio, image_id: UUID):
    image = await pg.get_image(image_id)

    if not image:
        raise ImageException.INVALID_IMAGE_ID

    tags = await pg.get_image_tags(image.id)
    url = minio.get_image(image.storage_key)

    return GetImageResponse(**image.dict(), url=url, tags=tags)


async def find_images_by_tags_datetime(
    tags: List[str],
    from_time: datetime,
    to_time: datetime,
    limit: int,
    offset: int,
    pg: Postgres,
    minio: Minio,
) -> List[GetImageResponse]:
    images = await pg.search_image_by_tags(
        tags,
        limit=limit,
        offset=offset,
        from_time=from_time,
        to_time=to_time,
    )

    result = []

    for img in images:
        url = minio.get_image(img.image.storage_key)
        tag_names = [t.name for t in img.tags]
        resp = GetImageResponse(**img.image.dict(), url=url, tags=tag_names)
        result.append(resp)

    return result


router = APIRouter()


@router.post("", response_model=UploadImageResponse)
async def upload_image(
    user: AuthenticatedUser = Depends(jwt_guard),
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

    if not tags:
        saved_image: Image = await pg.save_image(
            image.filename, storage_key, user.user_id
        )
        return UploadImageResponse(
            id=saved_image.id,
            name=image.filename,
            uploaded_by=saved_image.uploaded_by,
            created_at=saved_image.created_at,
        )

    split_tags = tags.split(",")
    tagged_image: TaggedImage = await pg.save_tagged_image(
        image.filename, storage_key, user.user_id, split_tags
    )
    return UploadImageResponse(
        id=tagged_image.image.id,
        name=image.filename,
        uploaded_by=tagged_image.image.uploaded_by,
        created_at=tagged_image.image.created_at,
        tags=split_tags,
    )


@router.get("/", response_model=List[GetImageResponse])
async def get_specific_image(
    image_id: Optional[UUID] = None,
    tags: Optional[str] = None,
    from_time: datetime = datetime.fromtimestamp(0),
    to_time: datetime = datetime.now(),
    limit: int = 5,
    offset: int = 0,
    user: AuthenticatedUser = Depends(jwt_guard),
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
        valid_tags, from_time, to_time, limit, offset, pg, minio
    )

    return resp
