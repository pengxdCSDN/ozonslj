from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, HttpUrl, PostgresDsn, RedisDsn, model_validator
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
    # 正式运行只允许 PostgreSQL 保存业务事实；该连接串必须由部署环境注入，
    # 禁止把用户名、密码或云数据库地址写入仓库、镜像或前端构建产物。
    database_url: PostgresDsn | None = None
    # Redis 只保存可恢复队列、锁、限流和短期协调状态，不能作为业务事实来源。
    redis_url: RedisDsn | None = None
    # 当前产品按单一运营组织交付；该值只用于服务端绑定内部数据边界，客户端不得选择或覆盖。
    default_organization_id: str = Field(default="org-default", min_length=1, max_length=120)
    session_cookie_secure: bool = False
    login_max_attempts: int = Field(default=5, ge=1, le=20)
    login_window_seconds: int = Field(default=300, ge=60, le=3600)
    ozon_mode: Literal["stub", "live"] = "stub"
    ozon_base_url: HttpUrl = HttpUrl("https://api-seller.ozon.ru")
    ozon_credential_key_file: Path = Path("secrets/ozon_credential_key")
    ozon_credential_key_version: int = Field(default=1, ge=1)
    # 同步进程采用低并发轮询以适配 2 核 2GB 云服务器；这些值只控制调度节奏，
    # 任务事实和重试次数仍以 PostgreSQL 中的 sync_jobs 为准。
    sync_dispatch_interval_seconds: float = Field(default=5.0, ge=0.5, le=60.0)
    sync_dispatch_batch_size: int = Field(default=100, ge=1, le=500)
    sync_worker_block_ms: int = Field(default=1_000, ge=100, le=10_000)
    sync_worker_lease_seconds: int = Field(default=30, ge=10, le=300)
    sync_worker_retry_delay_seconds: int = Field(default=60, ge=1, le=3_600)
    log_level: LogLevel = "DEBUG"

    @model_validator(mode="after")
    def require_postgresql_and_cloud_runtime_dependencies(self) -> "Settings":
        """所有环境必须配置 PostgreSQL；生产环境还必须配置 Redis。"""
        missing: list[str] = []
        if self.database_url is None:
            missing.append("DATABASE_URL")
        if self.app_env == "production" and self.redis_url is None:
            missing.append("REDIS_URL")
        if missing:
            names = "、".join(missing)
            raise ValueError(f"运行环境缺少必需配置：{names}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
