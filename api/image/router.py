from fastapi import APIRouter, Depends, File, Form, UploadFile

from libs.dependencies import jwt_guard
from libs.exceptions import ImageException
from libs.utils import make_storage_key, validate_image_file
from model.auth import AuthenticatedUser
from model.http import GetImageResponse, UploadImageResponse
from model.postgres import Image, TaggedImage
from repository import Minio, Postgres, get_minio, get_pg

router = APIRouter()


@router.post("/upload", response_model=UploadImageResponse)
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


@router.get("/{image_id}", response_model=GetImageResponse)
async def get_specific_image(
    image_id: str,
    user: AuthenticatedUser = Depends(jwt_guard),
    minio: Minio = Depends(get_minio),
    pg: Postgres = Depends(get_pg),
):
    image = await pg.get_image(image_id)

    if not image:
        raise ImageException.INVALID_IMAGE_ID

    tags = await pg.get_image_tags(image.id)
    url = minio.get_image(image.storage_key)

    return GetImageResponse(**image.dict(), url=url, tags=tags)
