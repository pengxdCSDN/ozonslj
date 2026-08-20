"""说明本模块的职责、边界和主要协作对象。"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from backend.app.infrastructure.postgresql.migrations import migrate_postgres


@dataclass(frozen=True, slots=True)
class TenantContext:
    """一次数据库事务不可变的组织与用户授权上下文。"""

    organization_id: str
    user_id: str

    def __post_init__(self) -> None:
        """实现特殊方法 __post_init__，遵循该类型的 Python 运行时约定。"""
        if not self.organization_id.strip():
            raise ValueError("organization_id 不能为空")
        if not self.user_id.strip():
            raise ValueError("user_id 不能为空")


class PostgresSessionFactory:
    """提供带强制 RLS 上下文的短事务，禁止调用方直接借用裸连接。"""

    def __init__(
        self,
        database_url: str,
        *,
        min_size: int = 1,
        max_size: int = 5,
        pool: ConnectionPool[Connection[dict[str, Any]]] | None = None,
    ) -> None:
        """初始化对象依赖和运行时状态。"""
        if not database_url.strip():
            raise ValueError("database_url 不能为空")
        if min_size < 0 or max_size < 1 or min_size > max_size:
            raise ValueError("PostgreSQL 连接池大小无效")
        # API 默认最多占用 5 个连接，为 Worker、迁移、备份和运维预留云端
        # max_connections=30 的余量。连接池延迟打开，模块导入不会访问网络。
        self._database_url = database_url
        self._migrate_on_open = pool is None
        self._pool = pool or ConnectionPool(
            conninfo=database_url,
            min_size=min_size,
            max_size=max_size,
            open=False,
            kwargs={"row_factory": dict_row},
        )

    def open(self) -> None:
        """显式打开连接池并等待最小连接就绪，使启动失败可被部署平台观察。"""
        # API 与 Worker 都可能率先访问数据库；迁移运行器通过咨询锁串行化升级。
        # 升级失败时不开放连接池，避免新代码在旧 schema 上继续提供流量。
        if self._migrate_on_open:
            migrate_postgres(self._database_url)
        self._pool.open(wait=True)

    def close(self) -> None:
        """停止接收新借用并关闭池内连接。"""
        self._pool.close()

    def check(self) -> None:
        """执行最小只读查询，验证连接池能够取得可用 PostgreSQL 连接。"""
        with self._pool.connection() as connection:
            connection.execute("SELECT 1").fetchone()

    @contextmanager
    def transaction(
        self,
        context: TenantContext,
    ) -> Iterator[Connection[dict[str, Any]]]:
        """在同一事务内设置 RLS 上下文，并把连接交给参数化业务查询。"""
        with self._pool.connection() as connection, connection.transaction():
            # set_config(..., true) 与 SET LOCAL 等价，值只在当前事务有效；
            # 连接归还池前事务结束，避免租户上下文泄漏到下一位借用者。
            connection.execute(
                """
                SELECT
                    set_config('app.organization_id', %s, true),
                    set_config('app.user_id', %s, true)
                """,
                (context.organization_id, context.user_id),
            )
            yield connection

    @contextmanager
    def authentication_transaction(self) -> Iterator[Connection[dict[str, Any]]]:
        """提供登录前受限事务；仅身份适配器可先查用户，再在事务内补齐 RLS 上下文。"""
        with self._pool.connection() as connection, connection.transaction():
            yield connection
