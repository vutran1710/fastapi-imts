from datetime import datetime, timedelta
from os import environ
from random import sample
from typing import List, Tuple
from uuid import UUID, uuid4

import pytest
import pytest_asyncio  # noqa
import pytz
from asyncpg import Connection as PgConnection
from faker import Faker
from repository.postgres import Postgres
from settings import settings

fake = Faker()
Faker.seed(0)
tz = pytz.timezone(environ["TZ"])
pytestmark = pytest.mark.asyncio


class DataMocker:
    pg: PgConnection

    def __init__(self, pg):
        self.pg = pg

    async def create_images(self, count=1000):
        data = []

        for _ in range(count):
            image_id = uuid4()
            name = fake.file_name(category="image")
            delta = timedelta(days=_)
            created_at = (datetime(2000, 1, 1) + delta).replace(tzinfo=tz)
            values = (image_id, name, f"{image_id}__{name}", created_at)
            data.append(values)

        await self.pg.executemany(
            "INSERT INTO images (id, name, storage_key, created_at) VALUES ($1, $2, $3, $4)",
            tuple(data),
        )
        return [(item[0], item[3]) for item in data]

    async def create_tags(self, count=100):
        words = list(set(fake.words(nb=count)))

        await self.pg.executemany(
            "INSERT INTO tags (id, name) VALUES ($1, $2)",
            ((idx, w) for idx, w in enumerate(words)),
        )

        return list(range(len(words)))

    async def create_tagged(self, tags: List[int], images: Tuple[UUID, datetime]):
        values = []
        for img in images:
            img_tag = sample(tags, k=4)
            for t in img_tag:
                values.append((t, img[0], img[1]))

        await self.pg.executemany(
            "INSERT INTO tagged (tag, image, created_at) VALUES ($1, $2, $3)",
            values,
        )


async def test_insert_many():
    pg = await Postgres.init(settings)
    await pg.c.fetch("TRUNCATE tagged CASCADE")
    await pg.c.fetch("TRUNCATE images CASCADE")
    await pg.c.fetch("TRUNCATE tags RESTART IDENTITY CASCADE")
    dm = DataMocker(pg.c)
    images = await dm.create_images(count=100000)
    words = await dm.create_tags(count=50000)
    await dm.create_tagged(words, images)
