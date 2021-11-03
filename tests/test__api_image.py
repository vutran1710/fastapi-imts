"""Testing authentication flow of App
"""
from random import sample
from urllib.parse import parse_qs
from uuid import UUID

from faker import Faker
from logzero import logger as log

from model.http import UploadImageResponse

from .fixtures import API, pytestmark, setup  # noqa

fake = Faker()
Faker.seed(0)


async def test_image_upload(setup):  # noqa
    client, auth = setup("app", "auth")

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


async def test_upload_multi_image(setup):  # noqa
    client, auth, headers = setup("app", "auth", "headers")

    image_name = "my_image.jpeg"

    files = {
        "image": (image_name, bytearray("", encoding="utf-8"), "multipart/form-data")
    }

    # Upload multi images of same name should succeed
    # but different image-ids returned
    def upload():
        resp = client.post(API.upload_image, headers=headers, files=files)
        assert resp.status_code == 200
        return resp.json()["id"]

    ids = [upload() for _ in range(2)]
    assert ids[0] != ids[1]


async def test_upload_image_with_tags(setup):  # noqa
    client, auth, headers = setup("app", "auth", "headers")

    image_name = "my_image.jpeg"

    files = {
        "image": (image_name, bytearray("", encoding="utf-8"), "multipart/form-data"),
    }

    tags = fake.words(nb=10)

    def upload():
        tags_str = ",".join(sample(tags, 5))
        resp = client.post(
            API.upload_image,
            headers=headers,
            files=files,
            data={"tags": tags_str},
        )
        assert resp.status_code == 200
        data = resp.json()
        log.info(data["tags"])
        assert len(set(data["tags"])) == 5

    assert [upload() for _ in range(5)]


async def test_find_image_by_id(setup):  # noqa
    client, auth, headers = setup("app", "auth", "headers")

    tags = fake.words(nb=5)

    def make_files():
        name = fake.file_name(category="image")
        data = bytearray("", encoding="utf-8")
        return {"image": (name, data, "multipart/form-data")}

    def upload():
        tags_str = ",".join(sample(tags, 4))
        file = make_files()
        resp = client.post(
            API.upload_image,
            headers=headers,
            files=file,
            data={"tags": tags_str},
        )
        log.info(resp.text)
        log.info(file)
        assert resp.status_code == 200
        image_id = resp.json()["id"]
        return image_id

    image_ids = [upload() for _ in range(10)]

    log.info(image_ids)

    resp = client.get(API.find_one_image, headers=headers, params={"id": image_ids[0]})

    assert resp.status_code == 200
    log.info(resp.json())

    tags = resp.json()["tags"]
    assert len(tags) == 4


async def test_search_image(setup):  # noqa
    client, auth, headers = setup("app", "auth", "headers")

    tags = fake.words(nb=10)

    def make_files():
        name = fake.file_name(category="image")
        data = bytearray("", encoding="utf-8")
        return {"image": (name, data, "multipart/form-data")}

    def upload():
        tags_str = ",".join(sample(tags, 4))
        file = make_files()
        resp = client.post(
            API.upload_image,
            headers=headers,
            files=file,
            data={"tags": tags_str},
        )
        assert resp.status_code == 200
        image_id = resp.json()["id"]
        return image_id

    [upload() for _ in range(10)]

    found = client.get(
        API.find_many_images,
        headers=headers,
        params={"tags": ",".join(tags), "limit": 10},
    )

    assert found.status_code == 200
    found = found.json()

    data = found["data"]
    assert len(data) == 10

    # With pagination
    resp = client.get(
        API.find_many_images,
        headers=headers,
        params={"tags": ",".join(tags), "limit": 5},
    )

    resp = resp.json()
    next_link = resp["next"]
    images = resp["data"]
    assert len(images) == 5
    assert next_link != ""

    log.warn(images)

    params = parse_qs(next_link)
    log.warn(params)
    resp = client.get(
        API.find_many_images + "?" + next_link,
        headers=headers,
    )

    resp = resp.json()
    next_link = resp["next"]
    images = resp["data"]
    assert len(images) == 5
    assert next_link == ""
