from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from asyncpg import Connection, Record, connect
from asyncpg.exceptions import UniqueViolationError
from model.enums import Provider
from model.postgres import User
from settings import Settings

Records = List[Record]


class Q:
    FIND_USER_BY_EMAIL = "SELECT * FROM users WHERE email = $1"
    FIND_USER_BY_ID = "SELECT * FROM users WHERE id = $1"

    REGISTER_NEW_USER_APP = "INSERT INTO users (id, email, password, provider) VALUES ($1, $2, $3, 'app') RETURNING *"
    REGISTER_NEW_USER_SOCIAL = "INSERT INTO users (id, email, token, expire_at, provider) VALUES ($1, $2, $3, $4, $5) RETURNING *"

    UPDATE_USER_TOKEN = (
        "UPDATE users SET token = $1, expire_at = $2 WHERE email = $3 RETURNING *"
    )

    GET_USER_TOKEN = (
        "SELECT token FROM users WHERE email = $1 AND expire_at > current_timestamp"
    )

    INSERT_NEW_IMAGE = "INSERT INTO images (image_key, uploaded_by) VALUES ($1, $2)"

    async def prepare(self, conn: Connection):
        for a in dir(self):
            if a.isupper():
                query = getattr(self, a)
                prepared = await conn.prepare(query)
                setattr(self, a, prepared.fetch)


class Postgres:
    def __init__(self, conn: Connection, queries: Q):
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
        q = Q()
        await q.prepare(conn)
        return cls(conn, q)

    async def register_new_user(self, email: str, pwd: str) -> Optional[User]:
        """Register new user to database using email & password"""
        try:
            args = (uuid4(), email, pwd)
            records: Records = await self.q.REGISTER_NEW_USER_APP(*args)  # type: ignore
            return User(**records[0])
        except UniqueViolationError:
            return None

    async def get_user(self, email: str = None, user_id: str = None) -> Optional[User]:
        """Get user data from email or user_id, return User model"""
        if not email and not user_id:
            raise ValueError("At least email or user_id must be specified")

        records: Records = await (
            self.q.FIND_USER_BY_EMAIL(email)  # type: ignore
            if email
            else self.q.FIND_USER_BY_ID(user_id)  # type: ignore
        )

        return User(**records[0]) if records else None

    async def insert_or_update_user(
        self, email: str, token: str, timestamp: int, provider: Provider
    ) -> User:
        """Register/update user to database using his social-login"""
        time = datetime.fromtimestamp(timestamp)
        result = await self.q.FIND_USER_BY_EMAIL(email)  # type: ignore

        if not result:
            args = (uuid4(), email, token, time, provider)
            records: Records = await self.q.REGISTER_NEW_USER_SOCIAL(*args)  # type: ignore
            return User(**records[0])

        records: Records = await self.q.UPDATE_USER_TOKEN(token, time, email)  # type: ignore
        return User(**records[0])

    async def insert_new_image(self, image_key: str, uploader: str):
        await self.q.INSERT_NEW_IMAGE(image_key, uploader)  # type: ignore
