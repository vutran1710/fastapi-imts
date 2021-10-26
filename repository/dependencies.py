from settings import settings as st

from .http import Http
from .minio import Minio
from .postgres import PgRepo
from .redis import Redis


async def get_pg():
    pg = await PgRepo.init(st)
    yield pg


async def get_redis():
    redis = await Redis.init(st)
    yield redis


async def get_minio():
    minio = Minio.init(st)
    yield minio


async def get_http():
    http = Http()
    yield http
