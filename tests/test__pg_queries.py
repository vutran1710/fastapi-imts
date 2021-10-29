"""Unit testing the custom Postgres module
"""
from datetime import datetime

import pytest
import pytest_asyncio  # noqa
from asyncpg import Connection
from logzero import logger as log
from model.postgres import Image, Tag, TaggedImage, User
from repository.postgres import Postgres
from settings import settings

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

    # clean up
    await pg.c.fetch(f"DELETE FROM users WHERE email = '{new_user.email}'")


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

    # clean up
    await pg.c.fetch(f"DELETE FROM users WHERE email = '{new_user.email}'")


async def test_save_and_get_image(setup_pg):
    """Test saving and retrieving image from Posgres
    Image for upload requires filename and its uploader
    """
    pg = setup_pg

    user = ("dummy@vutr.io", "some-password-no-need-encrypting")
    user: User = await pg.save_user(*user)

    data = ("some-image.png", user.id)
    image: Image = await pg.save_image(*data)
    assert isinstance(image, Image)
    assert isinstance(image.id, int)
    assert image.uploaded_by == user.id
    assert image.image_key == data[0]

    # Retrieve image by image-key only
    get_image: Image = await pg.get_image(image.image_key)
    assert isinstance(get_image, Image)
    assert get_image.id == image.id
    assert get_image.image_key == image.image_key
    assert get_image.created_at

    non_exist = await pg.get_image("non-exist-image-key")
    assert non_exist is None

    # clean up
    # NOTE: image must be erased first due to foreign-key relationship to user table
    await pg.c.fetch(f"DELETE FROM images WHERE id = '{image.id}'")
    await pg.c.fetch(f"DELETE FROM users WHERE email = '{user.email}'")


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

    # cleanup
    tags = set(tags_list_1 + tags_list_2)
    for t in tags:
        await pg.c.fetch("DELETE FROM tags WHERE name = $1", t)


async def test_save_and_get_tagged_image(setup_pg):
    """Test saving and retrieving tagged image"""
    pg = setup_pg

    before_insert = await pg.c.fetchval("SELECT COUNT(*) FROM tagged")

    user = ("dummy@vutr.io", "some-password-no-need-encrypting")
    user: User = await pg.save_user(*user)

    tags = ["one", "two", "three"]
    data = ("some-image.png", user.id, tags)
    image: TaggedImage = await pg.save_tagged_image(*data)

    assert isinstance(image, TaggedImage)
    assert len(image.tags) == len(tags)

    after_insert = await pg.c.fetchval("SELECT COUNT(*) FROM tagged")

    assert after_insert == before_insert + len(tags)

    # clean up
    await pg.c.fetch(f"DELETE FROM images WHERE id = '{image.image.id}'")
    await pg.c.fetch(f"DELETE FROM users WHERE email = '{user.email}'")
