"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from collections.abc import Sequence
from decimal import Decimal

from psycopg_pool import AsyncConnectionPool

from backend.app.domain.product_offer import ProductOffer
from backend.app.infrastructure.postgres.migrations import migrate_postgres

_LOCAL_SELLER_ACCOUNT_ID = "local-stub-seller"
_LOCAL_WORKSPACE_ID = "local"
_MINOR_UNITS_PER_MAJOR = Decimal(100)


class PostgresDatabase:
    """管理 PostgreSQL 迁移、连接池和本地 Stub 种子数据。"""

    def __init__(self, dsn: str, *, min_size: int, max_size: int) -> None:
        """初始化对象依赖和运行时状态。

Args:
    dsn: 参数语义、输入边界和安全约束。
    min_size: 参数语义、输入边界和安全约束。
    max_size: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._dsn = dsn
        self.pool = AsyncConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            open=False,
        )

    async def open(self, *, seed_offers: Sequence[ProductOffer]) -> None:
        """执行 open 的业务流程并返回该流程的结果。

Args:
    seed_offers: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await asyncio.to_thread(migrate_postgres, self._dsn)
        await self.pool.open(wait=True, timeout=15)
        await self._seed_stub_workspace(seed_offers)

    async def close(self) -> None:
        """执行 close 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        await self.pool.close()

    async def ping(self) -> None:
        """执行 ping 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        async with self.pool.connection() as connection:
            await connection.execute("SELECT 1")

    async def _seed_stub_workspace(
        self,
        seed_offers: Sequence[ProductOffer],
    ) -> None:
        """执行内部步骤 _seed_stub_workspace，供同一模块的公开流程复用。

Args:
    seed_offers: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        async with self.pool.connection() as connection, connection.transaction():
            await connection.execute(
                """
                    INSERT INTO seller_accounts (id, display_name, status)
                    VALUES (%s, %s, 'disabled')
                    ON CONFLICT (id) DO NOTHING
                    """,
                (_LOCAL_SELLER_ACCOUNT_ID, "Local stub seller"),
            )
            await connection.execute(
                """
                    INSERT INTO store_workspaces (id, seller_account_id, name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                (_LOCAL_WORKSPACE_ID, _LOCAL_SELLER_ACCOUNT_ID, "Local workspace"),
            )
            for position, offer in enumerate(seed_offers):
                await connection.execute(
                    """
                        INSERT INTO product_offers (
                            workspace_id,
                            offer_id,
                            position,
                            ozon_product_id,
                            name,
                            price_minor,
                            currency,
                            available_stock
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (workspace_id, offer_id) DO NOTHING
                        """,
                    (
                        _LOCAL_WORKSPACE_ID,
                        offer.offer_id,
                        position,
                        offer.ozon_product_id,
                        offer.name,
                        _decimal_to_minor(offer.price),
                        offer.currency,
                        offer.available_stock,
                    ),
                )


def _decimal_to_minor(amount: Decimal) -> int:
    """执行内部步骤 _decimal_to_minor，供同一模块的公开流程复用。

Args:
    amount: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    minor_amount = amount * _MINOR_UNITS_PER_MAJOR
    if minor_amount != minor_amount.to_integral_value():
        raise ValueError(f"金额的小数位超过两位：{amount!r}")
    return int(minor_amount)
