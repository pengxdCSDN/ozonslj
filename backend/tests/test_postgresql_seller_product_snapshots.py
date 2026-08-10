import asyncio
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.seller_product_snapshots import (
    PostgresSellerProductSnapshotGateway,
)
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        del context
        yield self.connection


def test_product_snapshot_history_returns_summary_without_items() -> None:
    cursor = MagicMock()
    cursor.fetchall.return_value = [{
        "cursor": "next", "total": 3,
        "items": [{"offer_id": "SKU-1"}], "source": "seller_api",
    }]
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresSellerProductSnapshotGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)), TenantContext("org", "user")
    )

    result = asyncio.run(gateway.list_snapshots(workspace_id="workspace", limit=20))

    assert result[0].total == 3
    assert result[0].items == []
    assert result[0].dry_run is True
