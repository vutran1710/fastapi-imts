"""Testing authentication flow of App
"""
from datetime import datetime
from uuid import UUID, uuid4

from logzero import logger as log
from model.http import AuthResponse, FindImageResponse, UploadImageResponse

from .fixtures import API, pytestmark, setup  # noqa


async def test_image_upload(setup):  # noqa
    client, pg, minio, auth = setup("app", "pg", "minio", "auth")

    headers = {"Authorization": f"Bearer {auth.access_token}"}

    # Load a test image
    image_data = None

    with open("tests/sample.jpeg", "rb") as image:
        f = image.read()
        image_data = bytearray(f)
        image.close()

    image_name = "my_image.jpeg"

    files = {"image": (image_name, image_data, "multipart/form-data")}

    response = client.post(API.upload_image, headers=headers, files=files)

    assert response.status_code == 200

    resp = UploadImageResponse(**response.json())
    assert resp.tags == []
    assert isinstance(resp.id, UUID)
    assert resp.uploaded_by == auth.user_id
