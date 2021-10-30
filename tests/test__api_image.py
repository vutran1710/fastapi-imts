"""Testing authentication flow of App
"""
import pytest
import pytest_asyncio  # noqa
from fastapi.testclient import TestClient
from logzero import logger as log

from main import app
from model.http import AuthResponse, GetImageResponse, UploadImageResponse
from repository.minio import Minio
from repository.postgres import Postgres
from settings import settings

client = TestClient(app)

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def setup_pg():
    """Before each test, init a new Postgres instance
    Note that since each test case has its own event-loop,
    the pg instance must be created separately
    """
    pg = await Postgres.init(settings)
    minio = Minio.init(settings)

    yield pg, minio

    await pg.c.close()


async def test_image_upload(setup_pg):
    """Testing
    - Upload image with tag via form-data, must be authenticated first
    - Get image using image-key
    - Search image
    """
    pg, minio = setup_pg

    class API:
        signup = "v1/auth/sign-up"
        login = "v1/auth/login"
        upload = "v1/image/upload"
        get = "v1/image/"

    email, password = "image-uploader@vutr.io", "123123123"

    # Sign-up with valid credential should succeed
    response = client.post(
        API.signup,
        data={"username": email, "password": password},
    )

    if response.status_code == 400:
        response = client.post(
            API.login,
            data={"username": email, "password": password},
        )

    data = response.json()
    auth = AuthResponse(**data)

    # Load a test image
    image_data = None

    with open("tests/sample.jpeg", "rb") as image:
        f = image.read()
        image_data = bytearray(f)
        image.close()

    image_name = "my_image.jpeg"
    files = {"image": (image_name, image_data, "multipart/form-data")}

    # Upload image without tags
    response = client.post(
        API.upload,
        headers={"Authorization": f"Bearer {auth.access_token}"},
        files=files,
    )

    log.info(response.text)
    assert response.status_code == 200
    resp = UploadImageResponse(**response.json())
    assert resp.tags == []

    # Upload another image with same name should be fine, but the image id must be different
    response = client.post(
        API.upload,
        headers={"Authorization": f"Bearer {auth.access_token}"},
        files=files,
    )

    log.info(response.text)
    assert response.status_code == 200
    new_resp = UploadImageResponse(**response.json())
    assert new_resp.name == resp.name
    assert new_resp.id != resp.id

    # Upload image with tags should be ok
    tags = ["foo", "bar", "nono"]
    response = client.post(
        API.upload,
        headers={"Authorization": f"Bearer {auth.access_token}"},
        data={"tags": ",".join(tags)},
        files=files,
    )

    log.info(response.text)
    assert response.status_code == 200
    tagged = UploadImageResponse(**response.json())
    assert tagged.tags and len(tagged.tags) == 3

    # Upload invalid file with invalid name
    response = client.post(
        API.upload,
        headers={"Authorization": f"Bearer {auth.access_token}"},
        files={"image": ("invalid-name", image_data, "multipart/form-data")},
    )
    assert response.status_code == 400

    # Test get image by id
    tags = ["foo", "bar", "nono"]
    response = client.get(
        API.get + str(tagged.id),
        headers={"Authorization": f"Bearer {auth.access_token}"},
    )

    assert response.status_code == 200
    log.info(image)
    image: GetImageResponse = GetImageResponse(**response.json())
    assert image.id == tagged.id
    assert image.name == image.name
    assert str(image.uploaded_by) == auth.user_id
    assert image.tags and len(image.tags) == 3
    assert image.url
    assert image.created_at

    # Getting an invalid image id
    response = client.get(
        API.get + "invalid-image-id",
        headers={"Authorization": f"Bearer {auth.access_token}"},
    )
    assert response.status_code == 404

    # cleanup
    await pg.c.fetch("DELETE FROM users WHERE email = $1", email)
    await pg.c.executemany(
        "DELETE FROM images WHERE id = $1",
        [(str(i),) for i in [resp.id, new_resp.id, tagged.id]],
    )
    await pg.c.executemany("DELETE FROM tags WHERE name = $1", [(t,) for t in tags])
