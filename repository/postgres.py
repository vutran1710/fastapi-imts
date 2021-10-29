from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from asyncpg import Connection, Record, connect
from model.enums import Provider
from model.postgres import Image, Tag, TaggedImage, User
from settings import Settings

Records = List[Record]


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
    INSERT INTO images (image_key, uploaded_by)
    VALUES ($1, $2)
    RETURNING *
    """

    FIND_IMAGE_BY_KEY = "SELECT * FROM images WHERE image_key = $1"

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
        record: Optional[Record] = await self.q.REGISTER_NEW_USER_APP(*args, method="fetchrow")  # type: ignore
        return User(**record) if record else None

    async def get_user(self, email: str = None, user_id: str = None) -> Optional[User]:
        """Get user data from email or user_id"""
        records: Records = await (
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
            record: Record = await self.q.REGISTER_NEW_USER_SOCIAL(*args, method="fetchrow")  # type: ignore
            return User(**record)

        args = (token, time, provider, email)
        record: Record = await self.q.UPDATE_USER_TOKEN(*args, method="fetchrow")  # type: ignore
        return User(**record)

    async def save_image(self, image_key: str, uploader: str) -> Image:
        record: Record = await self.q.INSERT_NEW_IMAGE(image_key, uploader, method="fetchrow")  # type: ignore
        return Image(**record)

    async def get_image(self, image_key: str) -> Optional[Image]:
        records: Records = await self.q.FIND_IMAGE_BY_KEY(image_key)  # type: ignore
        return Image(**records[0]) if records else None

    async def save_tags(self, tags: List[str]) -> List[Tag]:
        values = [(None, t) for t in tags]
        records: Records = await self.q.UPSERT_TAGS(values)
        return [Tag(**r) for r in records]

    async def save_tagged_image(self, image_key: str, uploader: str, tags: List[str]):
        image: Image = await self.get_image(image_key)

        if not image:
            image = await self.save_image(image_key, uploader)

        tags: List[Tag] = await self.save_tags(tags)
        data = [(tag.id, image.id) for tag in tags]

        await self.q.INSERT_TAGGED_IMAGE(data)

        return TaggedImage(image=image, tags=tags)
