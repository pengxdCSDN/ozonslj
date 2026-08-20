"""兼容旧导入路径，统一转发到当前 PostgreSQL 同步任务适配器。"""

from backend.app.infrastructure.postgresql.sync_jobs import PostgresSyncJobGateway

__all__ = ["PostgresSyncJobGateway"]
