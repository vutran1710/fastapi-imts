from logzero import logger

from settings import settings

logger.info("Setup env for Testing ==========================")

settings.STAGE = "test"
settings.PG_DATABASE = "testdb"
