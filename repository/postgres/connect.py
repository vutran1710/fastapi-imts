from datetime import datetime, timedelta
from typing import List, Optional, Union
from uuid import UUID, uuid4

from asyncpg import Connection, connect
from logzero import logger as log  # noqa

import repository.postgres.queries as PsqlQueries
from model.enums import Provider
from model.postgres import Image, Tag, TaggedImage, User
from settings import Settings


class PreparedStm:
    """Turn all raw queries into prepared-statements"""

    async def prepare(self, conn: Connection):
        query_names = [q for q in dir(PsqlQueries) if q.isupper()]

        for name in query_names:
            query_stm: str = getattr(PsqlQueries, name)

            async def __get_fetch__(query_statement: str):
                prepared = await conn.prepare(query_statement)

                async def wrapped(*args, method="fetch"):
                    nonlocal conn, prepared
                    fetcher = getattr(prepared, method)
                    result = await fetcher(*args)
                    return result

                return wrapped

            method = await __get_fetch__(query_stm)
            setattr(self, name, method)


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
        args = (email, pwd)
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
            args = (email, token, time, provider)
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
        uploader: int,
    ) -> Image:
        args = (uuid4(), image_name, storage_key, uploader)
        record = await self.q.INSERT_NEW_IMAGE(*args, method="fetchrow")  # type: ignore
        return Image(**record)

    async def get_image(self, id: UUID) -> Optional[TaggedImage]:
        record = await self.q.FIND_IMAGE_BY_ID(id, method="fetchrow")  # type: ignore

        if not record:
            return None

        image = Image(**record)
        tags = [Tag(name=t) for t in (record["tags"] or "").split(",") if t]

        return TaggedImage(image=image, tags=tags)

    async def save_tags(self, tags: List[str]) -> List[Tag]:
        values = [(None, t) for t in tags]
        records = await self.q.UPSERT_TAGS(values)  # type: ignore
        return [Tag(**r) for r in records]

    async def save_tagged_image(
        self,
        image_name: str,
        storage_key: str,
        uploader: int,
        tags: List[str],
    ) -> TaggedImage:
        image = await self.save_image(image_name, storage_key, uploader)
        saved_tags = await self.save_tags(tags) if tags else []
        data = [(tag.id, image.id, image.created_at) for tag in saved_tags]
        await self.q.INSERT_TAGGED_IMAGE(data)  # type: ignore
        return TaggedImage(image=image, tags=saved_tags, created_at=image.created_at)

    async def get_image_tags(self, image_id: Union[str, UUID]) -> List[str]:
        records = await self.q.GET_IMAGE_TAGS(image_id)  # type: ignore
        return [r["name"] for r in records]

    async def search_image_by_tags(
        self,
        tags: List[str],
        limit: int,
        previous_id: UUID = None,
        from_date=datetime.fromtimestamp(0),
        to_date=datetime.now() + timedelta(minutes=1),
    ) -> List[TaggedImage]:
        tag_param = [(None, t) for t in tags]
        records = []

        if not previous_id:
            params = (tag_param, limit, from_date, to_date)
            records = await self.q.SEARCH_TAGGED_IMAGES(*params)  # type: ignore
        else:
            params = (tag_param, limit, from_date, to_date, previous_id)
            records = await self.q.SEARCH_TAGGED_IMAGES_WITH_PAGE(*params)  # type: ignore

        result = []

        for r in records:
            image = Image(**r)
            tag_strings = r["tags"].split(",")
            img_tags = [Tag(name=t) for t in tag_strings]
            tagged_img = TaggedImage(
                image=image,
                tags=img_tags,
                created_at=image.created_at,
            )
            result.append(tagged_img)

        return result
