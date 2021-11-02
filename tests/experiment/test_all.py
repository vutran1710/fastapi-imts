from random import choice, sample
from time import time

import pytest
import pytest_asyncio  # noqa
from faker import Faker
from logzero import logger as log  # noqa

from libs import make_storage_key
from repository.postgres import Postgres
from settings import settings

fake = Faker()
Faker.seed(0)

tags = []

pytestmark = pytest.mark.asyncio


async def create_users(pg: Postgres, count=10):
    users = []

    for _ in range(count):
        email = fake.email()
        user = await pg.save_user(email, "pwd")
        users.append(user.id) if user else None

    return users


async def flush(pg: Postgres):
    tables = ["users", "images", "tags"]

    for t in tables:
        await pg.c.fetch(f"DELETE FROM {t}")


@pytest.mark.skip(
    reason="activate only when inserting test data. Might take very long time"
)
async def test_insert_many_images():
    """Insert mock data into database for query testing"""
    global tags

    pg: Postgres = await Postgres.init(settings)

    await flush(pg)

    user_cnt = 100
    tag_cnt = 200

    users = await create_users(pg, count=user_cnt)
    tags = fake.words(nb=tag_cnt)

    log.info(tags)

    for _ in range(100000):
        name = fake.file_name(category="image")
        storage_key = make_storage_key(name)
        uploader = choice(users)
        tag_choices = sample(tags, 5)
        await pg.save_tagged_image(name, storage_key, uploader, tag_choices)


test_query = """
WITH tag_items AS (
        SELECT id, name
        FROM tags
        WHERE name IN (SELECT r.name FROM unnest($1::tags[]) as r)
),
image_ids AS (
        SELECT image
        FROM tagged
        WHERE tag in (select id from tag_items)
        LIMIT $2
        OFFSET $3
),
image_tag_ids AS (
        SELECT image, tag
        FROM tagged
        WHERE image in (SELECT image FROM image_ids)
),
image_tags AS (
        SELECT image, string_agg(tags.name, ', ') as tags
        FROM image_tag_ids
        LEFT JOIN tags
        ON image_tag_ids.tag = tags.id
        GROUP BY image
),
image_tags_full_info AS (
        SELECT images.*, image_tags.tags
        FROM image_tags
        LEFT JOIN images
        ON image_tags.image = images.id
)
SELECT * FROM image_tags_full_info
"""


@pytest.mark.skip(reason="activate only when exprimenting with large data set")
async def test_query_for_optimization():
    """Target:
    1Million images
    500k m2m relations
    Query:
    - 5 tags
    - limit: 50
    - offset: any
    - time: < 200ms
    """
    global tags, test_query

    pg: Postgres = await Postgres.init(settings)
    limit = 50
    offset = 0

    start = time()

    tags_for_search = sample(tags, 5)
    tags_for_search = [(None, n) for n in tags_for_search]
    log.info("Search Tags = %s", tags_for_search)

    result = await pg.c.fetch(test_query, tags_for_search, limit, offset)
    log.info(len(result))

    end = time()

    log.info("Duration = %s seconds", end - start)
