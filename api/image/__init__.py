from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from libs.dependencies import jwt_guard
from libs.utils import fix_image_name, raise_if_falsy, validate_image_file
from model.auth import AuthenticatedUser
from repository import Minio, Postgres, get_minio, get_pg

router = APIRouter()


@router.post("/upload")
async def upload_image(
    user: AuthenticatedUser = Depends(jwt_guard),
    image: UploadFile = File(...),
    content_length: int = Header(...),
    minio: Minio = Depends(get_minio),
    pg: Postgres = Depends(get_pg),
):
    """
    Upload Image
    - Maximum file size guard shall be handled by web-server ie  nginx or traefik
    - Only set data-length when uploading to Storage
    """
    valid = validate_image_file(image.filename)

    raise_if_falsy(HTTPException(400, "Only images allowed"), valid)

    filename = fix_image_name(image.filename)
    obj_name = minio.save_image(filename, filename.file)
    await pg.insert_new_image(obj_name, user.user_id)
