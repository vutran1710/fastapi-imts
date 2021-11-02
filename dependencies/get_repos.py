from repository import Http, MetricCollector, Minio, Postgres, Redis
from settings import settings as st

pg, minio, mc, rd = None, None, None, None


async def get_pg():
    """Tricky situation
    - During Testing, avoid using global-var / singleton since
    it can be very unstable with how event-loop behaves in Test
    - For the app running in other stage, use global-var to avoid
    re-initializaing connections for every incoming request
    """
    global pg

    if st.STAGE == "test":
        test_pg = await Postgres.init(st)
        yield test_pg
        return

    if not pg:
        pg = await Postgres.init(st)

    yield pg


async def get_minio():
    global minio

    if st.STAGE == "test":
        test_minio = Minio.init(st)
        yield test_minio
        return

    if not minio:
        minio = Minio.init(st)

    yield minio


async def get_mc():
    global mc

    if st.STAGE == "test":
        test_mc = await MetricCollector.init(st)
        yield test_mc
        return

    if not mc:
        mc = await MetricCollector.init(st)

    yield mc


async def get_redis():
    global rd

    if st.STAGE == "test":
        test_rd = await Redis.init(st)
        yield test_rd
        return

    if not rd:
        rd = await Redis.init(st)

    yield rd


async def get_http():
    http = Http()
    yield http
