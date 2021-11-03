from os import environ

from logzero import logger

from settings import settings

logger.info("Setup env for Testing ==========================")

settings.STAGE = "test"
settings.PG_DATABASE = "testdb"
environ["TZ"] = "Asia/Ho_Chi_Minh"
