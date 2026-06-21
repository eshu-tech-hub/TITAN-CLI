from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "TITAN CLI"
    app_version: str = "1.0.0"
    broker: str = "ANGEL_ONE"
    database: str = "titan.db"
    log_level: str = "INFO"
    environment: str = "development"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
