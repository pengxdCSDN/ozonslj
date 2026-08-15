from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import Field, HttpUrl, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ServiceRole = Literal["api", "worker", "scheduler"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "production"] = "local"
    # 进程角色用于最小化 Secret 挂载；调度器只投递任务，不应要求模型凭据。
    service_role: ServiceRole = "api"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    # 正式运行只允许 PostgreSQL 保存业务事实；该连接串必须由部署环境注入，
    # 禁止把用户名、密码或云数据库地址写入仓库、镜像或前端构建产物。
    database_url: PostgresDsn | None = None
    # Chroma 仅保存已发布知识切片的可重建向量；本地/测试环境可以不配置。
    chroma_url: HttpUrl | None = None
    # 商品翻译和 Embedding 仅调用云端 HTTPS 服务；API Key 由部署 Secret 注入，
    # 不写入代码、浏览器存储、日志或 Chroma 元数据。空值表示尚未启用真实云端模型。
    rag_embedding_provider: str | None = None
    rag_embedding_base_url: HttpUrl | None = None
    rag_embedding_model: str = "text-embedding-v4"
    rag_embedding_dimension: int = Field(default=1024, ge=64, le=2048)
    rag_embedding_api_key: str | None = Field(default=None, repr=False)
    rag_embedding_api_key_file: Path | None = Field(default=None, repr=False)
    rag_translation_provider: str | None = None
    rag_translation_base_url: HttpUrl | None = None
    rag_translation_model: str | None = None
    rag_translation_api_key: str | None = Field(default=None, repr=False)
    rag_translation_api_key_file: Path | None = Field(default=None, repr=False)
    # 供应商配置页面写入的 API Key 放在应用容器的受限可写目录；数据库只保存引用和末尾掩码。
    rag_provider_credentials_dir: Path = Path("/var/lib/ozonslj/rag-providers")
    postgres_host: str | None = None
    postgres_port: int = 5432
    postgres_database: str = "ozonslj"
    postgres_user: str = "ozonslj"
    postgres_password_file: Path | None = None
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
        if self.service_role != "scheduler":
            for env_name, key_name, file_name in (
                ("RAG_EMBEDDING_API_KEY", "rag_embedding_api_key", "rag_embedding_api_key_file"),
                ("RAG_TRANSLATION_API_KEY", "rag_translation_api_key", "rag_translation_api_key_file"),
            ):
                if getattr(self, key_name) is None and getattr(self, file_name) is not None:
                    path = getattr(self, file_name)
                    try:
                        secret = path.read_text(encoding="utf-8").strip()
                    except OSError:
                        secret = ""
                    if secret:
                        object.__setattr__(self, key_name, secret)
                    elif self.app_env == "production":
                        missing.append(env_name)
        if self.database_url is None:
            # 云端 Compose 使用 POSTGRES_* 与 password file 注入，避免把数据库密码
            # 写入普通环境变量；本地和测试仍可直接传 DATABASE_URL。
            if self.postgres_host and self.postgres_password_file:
                try:
                    password = self.postgres_password_file.read_text(encoding="utf-8").strip()
                except OSError:
                    password = ""
                if password:
                    username = quote(self.postgres_user, safe="")
                    encoded_password = quote(password, safe="")
                    dsn = (
                        f"postgresql://{username}:{encoded_password}"
                        f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
                    )
                    object.__setattr__(self, "database_url", PostgresDsn(dsn))
                else:
                    missing.append("DATABASE_URL")
            else:
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
