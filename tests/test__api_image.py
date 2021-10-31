"""Testing authentication flow of App
"""
from logzero import logger as log

from model.http import AuthResponse, GetImageResponse, UploadImageResponse

from .fixtures import API, pytestmark, setup  # noqa


async def test_image_upload(setup):  # noqa
    """Testing
    - Upload image with tag via form-data, must be authenticated first
    - Get image using image-key
    - Search image
    """
    client, pg, minio = setup

    email, password = "image-uploader@vutr.io", "123123123"

    # Sign-up with valid credential should succeed
    response = client.post(
        API.signup,
        data={"username": email, "password": password},
    )

    data = response.json()
    auth = AuthResponse(**data)
    headers = {"Authorization": f"Bearer {auth.access_token}"}

    # Load a test image
    image_data = None

    with open("tests/sample.jpeg", "rb") as image:
        f = image.read()
        image_data = bytearray(f)
        image.close()

    image_name = "my_image.jpeg"
    files = {"image": (image_name, image_data, "multipart/form-data")}

    # Upload image without tags
    response = client.post(API.upload_image, headers=headers, files=files)

    log.info(response.text)
    assert response.status_code == 200
    resp = UploadImageResponse(**response.json())
    assert resp.tags == []

    # Upload another image with same name should be fine, but the image id must be different
    response = client.post(API.upload_image, headers=headers, files=files)

    log.info(response.text)
    assert response.status_code == 200
    new_resp = UploadImageResponse(**response.json())
    assert new_resp.name == resp.name
    assert new_resp.id != resp.id

    # Upload image with tags should be ok
    tags = ["foo", "bar", "nono"]
    data = {"tags": ",".join(tags)}
    response = client.post(API.upload_image, headers=headers, data=data, files=files)

    log.info(response.text)
    assert response.status_code == 200
    tagged = UploadImageResponse(**response.json())
    assert tagged.tags and len(tagged.tags) == 3

    # Upload invalid file with invalid name
    invalid_files = {"image": ("invalid-name", image_data, "multipart/form-data")}
    response = client.post(API.upload_image, headers=headers, files=invalid_files)
    assert response.status_code == 400

    # Test get image by id
    tags = ["foo", "bar", "nono"]
    response = client.get(API.get_image + str(tagged.id), headers=headers)

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
    response = client.get(API.get_image + "invalid-image-id", headers=headers)
    assert response.status_code == 404
