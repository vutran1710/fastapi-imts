from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from model.auth import AuthenticatedUser
from model.metrics import UserTracking
from settings import Settings


class Collections:
    USERS = "tracking_users"


class MetricCollector:
    """For simplicity sake, use MongoDB to collect metrics"""

    def __init__(self, conn: AsyncIOMotorClient):
        self.c = conn
        self.db = conn.get_default_database()

    @classmethod
    async def init(cls, st: Settings):
        client = AsyncIOMotorClient(
            st.MONGO_CONNECTION_STRING,
            serverSelectionTimeoutMS=5000,
        )
        return cls(client)

    async def healthz(self) -> bool:
        """Check if a connection has been established"""
        pong = await self.c.admin.command({"ping": 1})
        return pong == {"ok": 1.0}

    async def collect_user(
        self,
        user: AuthenticatedUser,
        url: str,
        extra: dict = None,
    ):
        timestamp = datetime.now().timestamp()

        tracking_data = UserTracking(
            user_id=user.user_id,
            email=user.email,
            request_url=url,
            timestamp=timestamp,
        ).dict()

        if extra and isinstance(extra, dict):
            tracking_data.update({"extra": extra})

        doc = await self.db[Collections.USERS].insert_one(tracking_data)

        return doc.inserted_id
