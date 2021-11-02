from datetime import timedelta

from aioredis import Redis, from_url
from logzero import logger
from settings import Settings


class Keys:
    INVALID_TOKEN = "invalid_tokens"


class Redis:
    c: Redis

    def __init__(self, conn: Redis):
        self.c = conn

    @classmethod
    async def init(cls, st: Settings):
        client = from_url(st.REDIS_CONNECTION_STRING, decode_responses=True)
        return cls(client)

    async def ping(self) -> bool:
        pong = await self.c.ping()
        return pong

    async def invalidate_token(self, token: str, ttl: timedelta = None):
        pipe = self.c.pipeline(transaction=True)

        key = f"{Keys.INVALID_TOKEN}___{token}"
        p = pipe.set(key, "invalid")

        if ttl:
            p = p.expire(key, ttl.seconds)

        await p.execute()

    async def is_token_invalid(self, token) -> bool:
        key = f"{Keys.INVALID_TOKEN}___{token}"
        value = await self.c.get(key)
        return bool(value)
