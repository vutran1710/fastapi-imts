"""Unit testing the custom Postgres module
"""
from datetime import datetime
from os import environ
from random import sample
from uuid import UUID, uuid4

import pytest
import pytest_asyncio  # noqa
import pytz
from asyncpg import Connection
from faker import Faker
from logzero import logger as log

from libs import make_storage_key
from model.postgres import Image, Tag, TaggedImage, User
from repository.postgres import Postgres
from settings import settings

fake = Faker()
Faker.seed(0)
tz = pytz.timezone(environ["TZ"])
pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def setup_pg():
    """Before each test, init a new Postgres instance
    Note that since each test case has its own event-loop,
    the pg instance must be created separately
    """
    pg = await Postgres.init(settings)
    assert isinstance(pg.c, Connection)

    yield pg

    await pg.c.execute(
        """
    DELETE FROM tagged;
    DELETE FROM tags;
    DELETE FROM images;
    DELETE FROM users;
    """
    )

    await pg.c.close()


async def test_init(setup_pg):
    pg = setup_pg
    test_query = await pg.c.fetchval("SELECT 1 + 1")
    log.info(test_query)
    assert test_query == 2


async def test_save_user(setup_pg):
    """Test insert a new user to User table
    Fields required:
    - email
    - password
    """
    pg = setup_pg
    user = ("dummy@vutr.io", "some-password-no-need-encrypting")
    new_user: User = await pg.save_user(*user)
    log.debug("New user = %s", new_user)
    assert isinstance(new_user, User)
    assert new_user.email == user[0]

    # Trying to saving an already registered user will return None instead of raise error
    # The Philosophy here is, either None or Value, the http exception shall..
    # be handled by fastapi controller
    user = ("dummy@vutr.io", "wwww")
    result = await pg.save_user(*user)
    assert result is None

    # Retrieve user using email or user_id
    user: User = await pg.get_user(email=new_user.email)
    assert isinstance(user, User)
    assert user.id == new_user.id

    user: User = await pg.get_user(user_id=new_user.id)
    assert isinstance(user, User)
    assert user.id == new_user.id

    non_exist = await pg.get_user(email="non-exist@mail.com")
    assert non_exist is None


async def test_save_user_social(setup_pg):
    """Test insert a new user who using social-login to User table
    Fields required:
    - email
    - social-token
    - expire-at
    - provider: facebook | google
    """
    pg = setup_pg
    user = (
        "dummy@vutr.io",
        "facebook-token",
        datetime.now().timestamp(),
        "facebook",
    )
    new_user: User = await pg.save_social_user(*user)
    log.debug("New user = %s", new_user)

    assert isinstance(new_user, User)
    assert new_user.email == user[0]
    assert new_user.token == user[1]
    assert new_user.provider == user[3]

    # A registered social-logged-in user may need to update social-token,
    # or change social-login app
    # Saving user in such case should update token, expire-at and provider value
    user = (
        "dummy@vutr.io",
        "google-token",
        datetime.now().timestamp(),
        "google",
    )

    updated_user: User = await pg.save_social_user(*user)
    log.debug("Updated user = %s", updated_user)

    # ID should remain the same, other data updated
    assert updated_user.token == user[1]
    assert updated_user.provider == user[3]
    new_user.id == updated_user.id


async def test_save_and_get_image(setup_pg):
    """Test saving and retrieving image from Posgres
    Image for upload requires filename and its uploader
    """
    pg = setup_pg

    user = ("dummy@vutr.io", "some-password-no-need-encrypting")
    user: User = await pg.save_user(*user)

    image_name = "some-image.png"
    storage_key = make_storage_key(image_name)
    data = (image_name, storage_key, user.id)
    image: Image = await pg.save_image(*data)
    assert isinstance(image, Image)

    assert image.name == data[0]
    assert isinstance(image.id, UUID)
    assert image.uploaded_by == user.id
    assert image.storage_key == storage_key

    log.info(image)

    # Retrieve image by image-key only
    get_image = await pg.get_image(image.id)
    assert isinstance(get_image, TaggedImage)
    image = get_image.image
    assert image.id == image.id
    assert image.storage_key == image.storage_key
    assert image.uploaded_by == user.id
    assert image.created_at
    assert get_image.tags == []

    non_exist = await pg.get_image(uuid4())
    assert non_exist is None


async def test_save_tags(setup_pg):
    pg = setup_pg

    tags_list_1 = ["abc", "cde", "fgh"]
    tags = await pg.save_tags(tags_list_1)
    log.info(tags)

    assert len(tags) == 3

    for tag in tags:
        assert isinstance(tag, Tag)

    tags_list_2 = ["cde", "fgh", "kekk", "wow", "noob"]
    tags = await pg.save_tags(tags_list_2)
    log.info(tags)

    # Upsert OK, return ID for existing tag
    assert len(tags) == 5


async def test_save_and_get_tagged_image(setup_pg):
    """Test saving and retrieving tagged image"""
    pg = setup_pg

    before_insert = await pg.c.fetchval("SELECT COUNT(*) FROM tagged")

    user = ("dummy@vutr.io", "some-password-no-need-encrypting")
    user: User = await pg.save_user(*user)

    tags = ["one", "two", "three"]
    image_name = "some-image.png"
    storage_key = make_storage_key(image_name)
    data = (image_name, storage_key, user.id, tags)
    image: TaggedImage = await pg.save_tagged_image(*data)

    assert isinstance(image, TaggedImage)
    assert len(image.tags) == len(tags)

    after_insert = await pg.c.fetchval("SELECT COUNT(*) FROM tagged")

    assert after_insert == before_insert + len(tags)


async def test_search_image(setup_pg):
    global fake
    pg = setup_pg

    tags = fake.words(nb=100)
    tags_to_search = tags[:2]

    cnt = 0
    image_cnt = 50

    for _ in range(image_cnt):
        name = fake.file_name(category="image")
        key = make_storage_key(name)
        image_tags = sample(tags, 3)

        if any(t in image_tags for t in tags_to_search):
            cnt += 1

        await pg.save_tagged_image(name, key, None, image_tags)

    count = await pg.c.fetchval("SELECT COUNT(*) FROM images")
    assert count == image_cnt

    # Search image by tags
    search_images = await pg.search_image_by_tags(tags_to_search, image_cnt)
    log.info(
        "Search tags = %s, Found %s images, expected %s",
        tags_to_search,
        len(search_images),
        cnt,
    )

    assert len(search_images) == cnt

    # Image returned has at least one tag in the searching tag
    for img in search_images:
        image_tags = [t.name for t in img.tags]
        assert any(t in tags_to_search for t in image_tags)


async def test_search_with_datetime(setup_pg):
    global fake, tz
    pg = setup_pg

    tags = fake.words(nb=100)
    tags_to_search = []

    cnt = 0
    image_cnt = 29

    for day in range(image_cnt):
        name = fake.file_name(category="image")
        key = make_storage_key(name)
        image_tags = sample(tags, 3)

        img = await pg.save_tagged_image(name, key, None, image_tags)

        created_at = datetime(2021, 11, day + 1).replace(tzinfo=tz)

        # Check tags for image with created_at within 2021/11/1 ~ 2021/11/10
        if day < 10:
            tags_to_search.append(image_tags[0])
            cnt += 1

        # Sync created_at for 2 tables images & tagged
        await pg.c.fetch(
            "UPDATE images SET created_at = $1 WHERE id = $2",
            created_at,
            img.image.id,
        )

        await pg.c.fetch(
            "UPDATE tagged SET created_at = $1 WHERE image = $2",
            created_at,
            img.image.id,
        )

    from_date = datetime(2021, 11, 1).replace(tzinfo=tz)
    to_date = datetime(2021, 11, 10).replace(tzinfo=tz)

    search_images = await pg.search_image_by_tags(
        tags_to_search,
        image_cnt,
        from_date=from_date,
        to_date=to_date,
    )

    for i in search_images:
        assert from_date <= i.image.created_at <= to_date

    assert len(search_images) == cnt


async def test_search_with_pagination(setup_pg):
    global fake, tz
    pg = setup_pg

    tags = fake.words(nb=100)
    tags_to_search = []

    cnt = 0
    image_cnt = 9

    async def insert(day):
        nonlocal tags, cnt
        name = fake.file_name(category="image")
        key = make_storage_key(name)
        image_tags = sample(tags, 3)
        img = await pg.save_tagged_image(name, key, None, image_tags)
        created_at = datetime(2021, 10, day).replace(tzinfo=tz)

        if day < 10:
            tags_to_search.append(image_tags[0])
            cnt += 1

        await pg.c.fetch(
            "UPDATE images SET created_at = $1 WHERE id = $2",
            created_at,
            img.image.id,
        )

        await pg.c.fetch(
            "UPDATE tagged SET created_at = $1 WHERE image = $2",
            created_at,
            img.image.id,
        )

    for day in range(image_cnt):
        await insert(day + 1)

    all = await pg.search_image_by_tags(tags_to_search, 50)

    for i in all:
        log.warn("ALL >> %s  - t = %s", i.image.id, i.image.created_at)

    limit = 3
    images = await pg.search_image_by_tags(tags_to_search, limit + 1)

    log.warn("=========================================")
    for i in images:
        log.warn(">> %s  - t = %s", i.image.id, i.image.created_at)

    assert len(images) == limit + 1
    overlap_img = images[-1].image
    log.info(
        "Overlapping image = %s, time = %s", overlap_img.id, overlap_img.created_at
    )

    # Insert some more image on top and check if the pagination is still correct
    for _ in range(5):
        await insert(31)

    images = await pg.search_image_by_tags(
        tags_to_search,
        limit,
        to_date=images[-2].image.created_at,
        previous_id=images[-2].image.id,
    )
    log.warn("=========================================")
    for i in images:
        log.warn(">> %s  - t = %s", i.image.id, i.image.created_at)

    first_img = images[0].image

    log.info("first found image = %s, time = %s", first_img.id, first_img.created_at)

    assert first_img.id == overlap_img.id
