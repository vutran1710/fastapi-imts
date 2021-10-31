import pytest
import pytest_asyncio  # noqa
from asyncpg import Connection
from fastapi.testclient import TestClient

from main import app
from repository.minio import Minio
from repository.postgres import Postgres
from settings import settings

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def setup():
    client = TestClient(app)
    pg = await Postgres.init(settings)
    minio = Minio.init(settings)

    assert isinstance(pg.c, Connection)

    yield client, pg, minio

    await pg.c.execute(
        """
    DELETE FROM tagged;
    DELETE FROM tags;
    DELETE FROM images;
    DELETE FROM users;
    """
    )
    await pg.c.close()


class API:
    signup = "v1/auth/sign-up"
    login = "v1/auth/login"
    refresh = "v1/auth/refresh-token"

    upload_image = "v1/image"
    get_image = "v1/image/"

    add_tag = "v1/tag"
