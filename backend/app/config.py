from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "production"] = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_database: str = "ozonslj"
    postgres_user: str = "ozonslj"
    postgres_password_file: Path = Path("secrets/postgres_password")
    postgres_pool_min_size: int = 1
    postgres_pool_max_size: int = 4
    redis_url: str = "redis://127.0.0.1:6379/0"
    session_cookie_secure: bool = False
    login_max_attempts: int = Field(default=5, ge=1, le=20)
    login_window_seconds: int = Field(default=300, ge=60, le=3600)
    ozon_mode: Literal["stub", "live"] = "stub"
    ozon_base_url: HttpUrl = HttpUrl("https://api-seller.ozon.ru")
    ozon_client_id: str | None = None
    ozon_api_key: str | None = None
    log_level: LogLevel = "DEBUG"

    def postgres_dsn(self) -> str:
        """从受保护的密钥文件构造 PostgreSQL 连接串，不在配置中保存明文密码。"""

        password = self.postgres_password_file.read_text(encoding="utf-8").strip()
        if not password:
            raise ValueError("PostgreSQL 密码文件不能为空")
        return (
            f"postgresql://{quote_plus(self.postgres_user)}:{quote_plus(password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{quote_plus(self.postgres_database)}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
