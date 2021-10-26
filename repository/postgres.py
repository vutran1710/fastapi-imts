from datetime import datetime
from typing import List, Literal, Optional
from uuid import uuid4

from asyncpg import Connection, Record, connect
from asyncpg.exceptions import UniqueViolationError
from logzero import logger as log
from model.enums import Provider
from settings import Settings


class Q:
    FIND_BY_EMAIL = "SELECT id FROM users WHERE email = $1"
    GET_PASSWORD_BY_EMAIL = (
        "SELECT password FROM users WHERE email = $1 AND provider = 'app'"
    )
    REGISTER_NEW_USER = (
        "INSERT INTO users (id, email, password, provider) VALUES ($1, $2, $3, 'app')"
    )
    INSERT_NEW_USER = "INSERT INTO users (id, email, token, expire_at, provider) \
        VALUES ($1, $2, $3, $4, $5)"
    UPDATE_USER_TOKEN = "UPDATE users SET token = $1, expire_at = $2 WHERE email = $3"
    GET_USER_TOKEN = (
        "SELECT token FROM users WHERE email = $1 AND expire_at > current_timestamp"
    )
    REMOVE_USER_TOKEN = "UPDATE users SET token = null WHERE email = $1"

    async def prepare(self, conn: Connection):
        for a in dir(self):
            if a.isupper():
                query = getattr(self, a)
                prepared = await conn.prepare(query)
                setattr(self, a, prepared.fetch)


class PgRepo:
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

    async def register_new_user(self, email: str, pwd: str) -> bool:
        try:
            await self.q.REGISTER_NEW_USER(uuid4(), email, pwd)
            return True
        except UniqueViolationError:
            return False

    async def insert_user_if_needed(
        self,
        email: str,
        token: str,
        timestamp: int,
        provider: Provider,
    ):
        time = datetime.fromtimestamp(timestamp)
        result = await self.q.FIND_BY_EMAIL(email)  # type: ignore

        if not result:
            await self.q.INSERT_NEW_USER(  # type: ignore
                uuid4(),
                email,
                token,
                time,
                provider,
            )
            log.debug("Insert new user with email=%s", email)
        else:
            await self.q.UPDATE_USER_TOKEN(token, time, email)  # type: ignore
            log.debug("Update current user with new token")

    async def retrieve_password(self, email: str) -> str:
        records: List[Record] = await self.q.GET_PASSWORD_BY_EMAIL(email)  # type: ignore
        return records[0].get("password") if records else ""

    async def retrieve_user_token(self, email: str) -> Optional[str]:
        records: List[Record] = await self.q.GET_USER_TOKEN(email)  # type: ignore

        if not records:
            return None

        return records[0].get("token")

    async def remove_user_token(self, email: str):
        await self.q.REMOVE_USER_TOKEN(email)  # type: ignore
