"""Unit testing the custom Postgres module
"""
from datetime import datetime
from random import sample
from uuid import UUID, uuid4

import pytest
import pytest_asyncio  # noqa
from asyncpg import Connection
from faker import Faker
from logzero import logger as log

from libs import make_storage_key
from model.postgres import Image, Tag, TaggedImage, User
from repository.postgres import Postgres
from settings import settings

fake = Faker()
Faker.seed(0)

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

    # Retrieve image by image-key only
    get_image: Image = await pg.get_image(image.id)
    assert isinstance(get_image, Image)

    assert get_image.id == image.id
    assert get_image.storage_key == image.storage_key
    assert get_image.uploaded_by == user.id
    assert get_image.created_at

    non_exist = await pg.get_image("non-exist-image-key")
    assert non_exist is None

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
    assert image.created_at == image.image.created_at

    tags = await pg.get_image_tags(image.image.id)
    log.debug(tags)
    assert tags and len(tags) == 3
    for t in tags:
        assert isinstance(t, str)

    after_insert = await pg.c.fetchval("SELECT COUNT(*) FROM tagged")

    assert after_insert == before_insert + len(tags)


async def test_search_image(setup_pg):
    global fake
    pg = setup_pg

    tags = ["foo", "bar", "hello", "world", "goodbye", "wall"]

    for _ in range(100):
        image_name = fake.file_name(category="image")
        storage_key = make_storage_key(image_name)
        uploader = None
        image_tags = sample(tags, 2)
        image = await pg.save_tagged_image(
            image_name, storage_key, uploader, image_tags
        )

        random_created_time = fake.date_time()
        assert isinstance(random_created_time, datetime)
        await pg.c.fetch(
            "UPDATE images SET created_at = $1 WHERE id = $2",
            random_created_time,
            image.image.id,
        )
        await pg.c.fetch(
            "UPDATE tagged SET created_at = $1 WHERE image = $2",
            random_created_time,
            image.image.id,
        )

    count = await pg.c.fetchval("SELECT COUNT(*) FROM images")
    assert count == 100

    # Search image by tags
    tags_to_search = ["foo", "bar"]
    from_date, to_date = datetime(2000, 10, 10), datetime(2018, 10, 10)
    search_images = await pg.search_image_by_tags(
        tags_to_search,
        limit=3,
        from_date=from_date,
        to_date=to_date,
    )

    assert len(search_images) == 3

    for img in search_images:
        assert isinstance(img, TaggedImage)
        image_tags = [t.name for t in img.tags]
        # Image returned has at least one tag in the searching tag
        assert len(set(image_tags + tags_to_search)) < (
            len(image_tags) + len(tags_to_search)
        )
        assert from_date <= img.created_at <= to_date

    last_row_id = search_images[-1].image.id
    log.info("> Limit=3, Offset=0, Page=0 ==> last row %s", last_row_id)

    # Pagination with offset
    search_images = await pg.search_image_by_tags(
        tags_to_search,
        limit=3,
        offset=2,
        from_date=from_date,
        to_date=to_date,
    )

    assert len(search_images) == 3

    first_row_id = search_images[0].image.id
    log.info("> Limit=3, Offset=2, Page=1 ==> first row %s", first_row_id)

    # Overlapping
    assert last_row_id == first_row_id
