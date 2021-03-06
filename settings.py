from os import getenv
from typing import Literal

from pydantic import BaseSettings

Stage = Literal["production", "development", "test", "staging", "cicd"]


class Settings(BaseSettings):
    PG_HOST: str
    PG_USER: str
    PG_PWD: str
    PG_DATABASE: str
    PG_PORT: int = 5678
    MONGO_CONNECTION_STRING: str
    REDIS_CONNECTION_STRING: str
    STORAGE_HOST: str
    STORAGE_ACCESS_KEY: str
    STORAGE_SECRET_KEY: str
    STORAGE_BUCKET: str
    JWT_SECRET: str
    GOOGLE_APP_CLIENT_ID: str
    STAGE: Stage = "development"
    CORS_ORIGINS_ALLOWED: str = "*"

    class Config:
        env_file = getenv("DOTENV_FILE_PATH", ".env")

    @property
    def is_prod(self):
        return self.STAGE == "production"


settings = Settings()
