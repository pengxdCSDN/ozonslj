"""兼容旧导入路径，统一转发到当前 PostgreSQL 工作区适配器。"""

from backend.app.infrastructure.postgresql.store_workspaces import (
    PostgresStoreWorkspaceGateway,
)

__all__ = ["PostgresStoreWorkspaceGateway"]
