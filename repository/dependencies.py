from settings import settings as st

from .http import Http
from .minio import Minio
from .postgres import Postgres
from .redis import Redis

pg, minio = None, None


async def get_pg():
    """Tricky situation
    - During Testing, avoid using global-var / singleton since
    it can be very unstable with how event-loop behaves in Test
    - For the app running in other stage, use global-var to avoid
    re-initializaing connections for every incoming request
    """

    if st.STAGE == "test":
        test_pg = await Postgres.init(st)
        yield test_pg
        return

    global pg
    if not pg:
        pg = await Postgres.init(st)

    yield pg


async def get_redis():
    redis = await Redis.init(st)
    yield redis


async def get_minio():

    if st.STAGE == "test":
        test_minio = Minio.init(st)
        yield test_minio
        return

    global minio
    if not minio:
        minio = Minio.init(st)

    yield minio


async def get_http():
    http = Http()
    yield http
