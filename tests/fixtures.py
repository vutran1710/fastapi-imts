import pytest
import pytest_asyncio  # noqa
from asyncpg import Connection
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from main import app
from repository.metric_collector import Collections, MetricCollector
from repository.minio import Minio
from repository.postgres import Postgres
from settings import settings

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def setup():
    client = TestClient(app)
    pg = await Postgres.init(settings)
    minio = Minio.init(settings)
    mc = await MetricCollector.init(settings)

    assert isinstance(pg.c, Connection)
    assert isinstance(mc.c, AsyncIOMotorClient)
    assert isinstance(mc.db, AsyncIOMotorDatabase)

    yield client, pg, minio, mc

    await mc.db[Collections.USERS].delete_many({})

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
    search_image = "v1/image/search"

    add_tag = "v1/tag"
