from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID, uuid1, uuid4

from asyncpg import Connection, connect

from libs.utils import convert_string_to_uuid
from model.enums import Provider
from model.postgres import Image, Tag, TaggedImage, User
from settings import Settings


class Query:
    FIND_USER_BY_EMAIL = "SELECT * FROM users WHERE email = $1"

    FIND_USER_BY_ID = "SELECT * FROM users WHERE id = $1"

    REGISTER_NEW_USER_APP = """
    INSERT INTO users (id, email, password, provider)
    VALUES ($1, $2, $3, 'app')
    ON CONFLICT DO NOTHING
    RETURNING *
    """

    REGISTER_NEW_USER_SOCIAL = """
    INSERT INTO users (id, email, token, expire_at, provider)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING *
    """

    UPDATE_USER_TOKEN = """
    UPDATE users
    SET token = $1, expire_at = $2, provider = $3
    WHERE email = $4 RETURNING *
    """

    GET_USER_TOKEN = """
    SELECT token
    FROM users
    WHERE email = $1 AND expire_at > current_timestamp
    """

    INSERT_NEW_IMAGE = """
    INSERT INTO images (id, name, storage_key, uploaded_by)
    VALUES ($1, $2, $3, $4)
    RETURNING *
    """

    FIND_IMAGE_BY_ID = "SELECT * FROM images WHERE id = $1"

    UPSERT_TAGS = """
    WITH items (name) AS (SELECT r.name FROM unnest($1::tags[]) as r),
         added        AS
    (
        INSERT INTO tags (name)
        SELECT name FROM items
        EXCEPT
        SELECT name FROM tags
        RETURNING id, name
    )

    SELECT id, name FROM added
    UNION ALL
    SELECT id, name FROM tags
    WHERE name IN (SELECT name FROM items)
    """

    INSERT_TAGGED_IMAGE = """
    INSERT INTO tagged (tag, image)
    (SELECT r.tag, r.image FROM unnest($1::tagged[]) as r)
    RETURNING *
    """

    GET_IMAGE_TAGS = """
    WITH items (tag) AS (SELECT tag FROM tagged WHERE image = $1)
    SELECT name
    FROM tags
    RIGHT JOIN items
    ON tags.id = items.tag
    """

    async def prepare(self, conn: Connection):
        for a in dir(self):
            if a.isupper():
                query: str = getattr(self, a)

                def __get_fetch__(query_statement: str):
                    async def wrapped(*args, method="fetch"):
                        nonlocal conn
                        prepared = await conn.prepare(query_statement)
                        fetcher = getattr(prepared, method)
                        result = await fetcher(*args)
                        return result

                    return wrapped

                setattr(self, a, __get_fetch__(query))


class Postgres:
    def __init__(self, conn: Connection, queries: Query):
        self.c = conn
        self.q = queries

    @classmethod
    async def init(cls, st: Settings):
        conn = await connect(
            user=st.PG_USER,
            password=st.PG_PWD,
            database=st.PG_DATABASE,
            host=st.PG_HOST,
            port=st.PG_PORT,
        )
        q = Query()
        await q.prepare(conn)
        return cls(conn, q)

    async def save_user(self, email: str, pwd: str) -> Optional[User]:
        """Register new user to database using email & password"""
        args = (uuid4(), email, pwd)
        record = await self.q.REGISTER_NEW_USER_APP(*args, method="fetchrow")  # type: ignore
        return User(**record) if record else None

    async def get_user(self, email: str = None, user_id: str = None) -> Optional[User]:
        """Get user data from email or user_id"""
        records = await (
            self.q.FIND_USER_BY_EMAIL(email)  # type: ignore
            if email
            else self.q.FIND_USER_BY_ID(user_id)  # type: ignore
        )
        return User(**records[0]) if records else None

    async def save_social_user(
        self, email: str, token: str, timestamp: int, provider: Provider
    ) -> User:
        """Register/update user to database using his social-login"""
        time = datetime.fromtimestamp(timestamp)
        result = await self.q.FIND_USER_BY_EMAIL(email)  # type: ignore

        if not result:
            args = (uuid4(), email, token, time, provider)
            record = await self.q.REGISTER_NEW_USER_SOCIAL(*args, method="fetchrow")  # type: ignore
            return User(**record)

        record = await self.q.UPDATE_USER_TOKEN(
            token,
            time,
            provider,
            email,
            method="fetchrow",
        )  # type: ignore
        return User(**record)

    async def save_image(
        self,
        image_name: str,
        storage_key: str,
        uploader: str,
    ) -> Image:
        args = (uuid1(), image_name, storage_key, uploader)
        record = await self.q.INSERT_NEW_IMAGE(*args, method="fetchrow")  # type: ignore
        return Image(**record)

    async def get_image(self, image_id: Union[str, UUID]) -> Optional[Image]:
        if isinstance(image_id, str) and not convert_string_to_uuid(image_id):
            return None

        image_id = str(image_id)
        records = await self.q.FIND_IMAGE_BY_ID(image_id)  # type: ignore
        return Image(**records[0]) if records else None

    async def save_tags(self, tags: List[str]) -> List[Tag]:
        values = [(None, t) for t in tags]
        records = await self.q.UPSERT_TAGS(values)  # type: ignore
        return [Tag(**r) for r in records]

    async def save_tagged_image(
        self,
        image_name: str,
        storage_key: str,
        uploader: str,
        tags: List[str],
    ) -> TaggedImage:
        image = await self.get_image(storage_key)

        if not image:
            image = await self.save_image(image_name, storage_key, uploader)

        saved_tags = await self.save_tags(tags)
        data = [(tag.id, image.id) for tag in saved_tags]

        await self.q.INSERT_TAGGED_IMAGE(data)  # type: ignore

        return TaggedImage(image=image, tags=saved_tags)

    async def get_image_tags(self, image_id: Union[str, UUID]) -> List[str]:
        records = await self.q.GET_IMAGE_TAGS(image_id)  # type: ignore
        return [r["name"] for r in records]
