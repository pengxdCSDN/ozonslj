from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "production"] = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_path: Path = Path("data/ozonslj.db")
    ozon_mode: Literal["stub", "live"] = "stub"
    ozon_base_url: HttpUrl = HttpUrl("https://api-seller.ozon.ru")
    ozon_client_id: str | None = None
    ozon_api_key: str | None = None
    log_level: str = "DEBUG"


@lru_cache
def get_settings() -> Settings:
    return Settings()
