import asyncio
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.seller_stock_snapshots import (
    PostgresSellerStockSnapshotGateway,
)
from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        del context
        yield self.connection


def test_stock_snapshot_history_returns_summary() -> None:
    cursor = MagicMock()
    cursor.fetchall.return_value = [{"cursor": None, "total": 2, "source": "seller_api"}]
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresSellerStockSnapshotGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)), TenantContext("org", "user")
    )
    result = asyncio.run(gateway.list_snapshots(workspace_id="workspace"))
    assert result[0].total == 2
    assert result[0].items == []
