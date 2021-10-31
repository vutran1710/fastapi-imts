from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID, uuid1, uuid4

import repository.postgres.queries as PsqlQueries
from asyncpg import Connection, connect
from libs.utils import convert_string_to_uuid
from model.enums import Provider
from model.postgres import Image, Tag, TaggedImage, User
from settings import Settings


class PreparedStm:
    """Turn all raw queries into prepared-statements"""

    async def prepare(self, conn: Connection):
        for a in dir(PsqlQueries):
            if a.isupper():
                query: str = getattr(PsqlQueries, a)

                async def __get_fetch__(query_statement: str):
                    prepared = await conn.prepare(query_statement)

                    async def wrapped(*args, method="fetch"):
                        nonlocal conn, prepared
                        fetcher = getattr(prepared, method)
                        result = await fetcher(*args)
                        return result

                    return wrapped

                method = await __get_fetch__(query)
                setattr(self, a, method)


class Postgres:
    def __init__(self, conn: Connection, queries: PreparedStm):
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
        q = PreparedStm()
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

        record = await self.q.UPDATE_USER_TOKEN(  # type: ignore
            token,
            time,
            provider,
            email,
            method="fetchrow",
        )
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
        data = [(tag.id, image.id, image.created_at) for tag in saved_tags]

        await self.q.INSERT_TAGGED_IMAGE(data)  # type: ignore

        return TaggedImage(image=image, tags=saved_tags, created_at=image.created_at)

    async def get_image_tags(self, image_id: Union[str, UUID]) -> List[str]:
        records = await self.q.GET_IMAGE_TAGS(image_id)  # type: ignore
        return [r["name"] for r in records]

    async def search_image_by_tags(
        self,
        tags: List[str],
        limit: int = 5,
        offset: int = 0,
        from_time=datetime.fromtimestamp(0),
        to_time=datetime.now(),
    ) -> List[TaggedImage]:
        tag_param = [(None, t) for t in tags]
        records = await self.q.SEARCH_TAGGED_IMAGES_BY_TAGS(  # type: ignore
            tag_param, from_time, to_time, limit, offset
        )

        images = [Image(**r) for r in records]
        values = [(None, i.id, None) for i in images]
        records = await self.q.GET_TAGS_FOR_MULTIPLE_IMAGES(values)  # type: ignore

        image_tags = {}

        for record in records:
            image_id, tags = record["image"], record["tags"].split(",")
            image_tags.update({image_id: [Tag(name=t) for t in tags]})

        tagged_image = [
            TaggedImage(image=i, tags=image_tags[i.id], created_at=i.created_at)
            for i in images
        ]

        return tagged_image
