import pytest
import pytest_asyncio  # noqa
from aioredis import Redis as RedisConnection
from asyncpg import Connection
from fastapi.testclient import TestClient
from main import app
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from repository.metric_collector import Collections, MetricCollector
from repository.minio import Minio
from repository.postgres import Postgres
from repository.redis import Redis
from settings import settings

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def setup():
    client = TestClient(app)
    pg = await Postgres.init(settings)
    minio = Minio.init(settings)
    mc = await MetricCollector.init(settings)
    rd = await Redis.init(settings)

    assert isinstance(pg.c, Connection)
    assert isinstance(mc.c, AsyncIOMotorClient)
    assert isinstance(mc.db, AsyncIOMotorDatabase)
    assert isinstance(rd.c, RedisConnection)

    assert (await rd.ping()) is True

    current_db_name = await pg.c.fetchval(" SELECT current_database()")
    assert "test" in current_db_name

    yield client, pg, minio, mc, rd

    await mc.db[Collections.TRACKING_USERS].delete_many({})

    await pg.c.execute(
        """
    DELETE FROM tagged;
    DELETE FROM tags;
    DELETE FROM images;
    DELETE FROM users;
    """
    )
    await pg.c.close()

    await rd.c.flushall()


class API:
    signup = "v1/auth/sign-up"
    login = "v1/auth/login"
    refresh = "v1/auth/refresh-token"
    logout = "v1/auth/logout"

    upload_image = "v1/image"
    find_images = "v1/image/find"

    add_tag = "v1/tag"
