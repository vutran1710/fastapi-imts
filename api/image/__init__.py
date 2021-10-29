from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from libs.dependencies import jwt_guard
from libs.exceptions import ImageException
from libs.utils import fix_image_name, raise_if_falsy, validate_image_file
from model.auth import AuthenticatedUser
from model.http import GetImageResponse
from model.postgres import Image
from repository import Minio, Postgres, get_minio, get_pg

router = APIRouter()


@router.post("/upload")
async def upload_image(
    user: AuthenticatedUser = Depends(jwt_guard),
    image: UploadFile = File(...),
    minio: Minio = Depends(get_minio),
    pg: Postgres = Depends(get_pg),
):
    """
    Upload Image
    - Maximum file size guard shall be handled by web-server ie  nginx or traefik
    """
    valid = validate_image_file(image.filename)

    raise_if_falsy(ImageException.IMAGE_ONLY, valid)

    file_name = fix_image_name(image.filename)
    obj_name = minio.save_image(file_name, image.file)
    await pg.insert_new_image(obj_name, user.user_id)
    return obj_name


@router.get("/{image_key}", response_model=GetImageResponse)
async def get_specific_image(
    image_key: str,
    user: AuthenticatedUser = Depends(jwt_guard),
    minio: Minio = Depends(get_minio),
    pg: Postgres = Depends(get_pg),
):
    image: Image = await pg.get_image(image_key)

    raise_if_falsy(ImageException.INVALID_IMAGE_KEY, image)

    url = minio.get_image(image.image_key)

    return GetImageResponse(**image.dict(), url=url)
