"""Testing authentication flow of App
"""
from random import sample
from uuid import uuid1

from logzero import logger as log
from model.http import AuthResponse, GetImageResponse, UploadImageResponse

from .fixtures import API, pytestmark, setup  # noqa


async def test_image_upload(setup):  # noqa
    """Testing
    - Upload image with tag via form-data, must be authenticated first
    - Get image using image-key
    - Search image
    """
    client, pg, minio, _ = setup

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

    # Test find image by id
    tags = ["foo", "bar", "nono"]
    params = {"image_id": str(tagged.id)}
    response = client.get(API.find_images, headers=headers, params=params)

    assert response.status_code == 200
    log.info(image)
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    image: GetImageResponse = GetImageResponse(**data[0])
    assert image.id == tagged.id
    assert image.name == image.name
    assert image.uploaded_by == auth.user_id
    assert image.tags and len(image.tags) == 3
    assert image.url
    assert image.created_at

    # Test find invalid image using invalid id
    params = {"image_id": "invalid-id"}
    response = client.get(API.find_images, params=params, headers=headers)
    assert response.status_code == 422

    params = {"image_id": uuid1()}
    response = client.get(API.find_images, params=params, headers=headers)
    assert response.status_code == 404

    # Upload multi images:
    tags = ["foo", "bar", "nono", "hello", "world", "goodbye", "heaven"]

    for _ in range(20):
        sample_tags = ",".join(sample(tags, 3))
        data = {"tags": sample_tags}
        response = client.post(
            API.upload_image, headers=headers, data=data, files=files
        )

    # Find multi images using tags
    params = {"tags": "foo,bar,hello", "limit": 3}
    response = client.get(API.find_images, headers=headers, params=params)
    assert response.status_code == 200
    data = response.json()
    log.info(data)

    assert len(data) == 3
    for item in data:
        assert GetImageResponse(**item)
