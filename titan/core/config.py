from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "TITAN CLI"
    app_version: str = "1.0.0"
    broker: str = "ANGEL_ONE"
    database: str = "titan.db"
    log_level: str = "INFO"
    environment: str = "development"
    gemini_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
