from aioredis import Connection, from_url
from logzero import logger as log

from settings import Settings


class Redis:
    def __init__(self, conn: Connection):
        self._c = conn

    @classmethod
    async def init(cls, st: Settings):
        client = from_url(st.REDIS_CONNECTION_STRING)
        log.info("Ping redis = %s", await client.ping())
        return cls(client)
