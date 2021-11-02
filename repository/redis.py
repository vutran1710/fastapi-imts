from datetime import timedelta

from aioredis import Redis as RedisConnection
from aioredis import from_url

from settings import Settings


class Keys:
    INVALID_TOKEN = "invalid_tokens"


class Redis:
    def __init__(self, conn: RedisConnection):
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
        pipe.set(key, "invalid")

        if ttl:
            pipe.expire(key, ttl.seconds)

        await pipe.execute()

    async def is_token_invalid(self, token) -> bool:
        key = f"{Keys.INVALID_TOKEN}___{token}"
        value = await self.c.get(key)
        return bool(value)
