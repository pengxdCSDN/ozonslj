import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)
from backend.app.infrastructure.postgresql.stock_positions import (
    PostgresStockPositionGateway,
)


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection
        self.received_context: TenantContext | None = None

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        self.received_context = context
        yield self.connection


def test_stock_query_is_scoped_and_maps_fulfillment_quantities() -> None:
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = {"total": 2}
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = [
        {
            "offer_id": "SKU-1",
            "warehouse_id": "WH-1",
            "warehouse_name": "测试仓",
            "fulfillment_type": "FBS",
            "available_quantity": 8,
            "reserved_quantity": 3,
            "synced_at": datetime.now(UTC),
        }
    ]
    connection = MagicMock()
    connection.execute.side_effect = [count_cursor, rows_cursor]
    sessions = FakeSessions(connection)
    context = TenantContext("org-default", "user-1")
    gateway = PostgresStockPositionGateway(
        cast(PostgresSessionFactory, sessions),
        context,
    )

    page = asyncio.run(
        gateway.list_stock_positions(workspace_id="store-1", cursor=None, limit=1)
    )

    assert sessions.received_context == context
    assert page.items[0].fulfillment_type == "FBS"
    assert page.items[0].available_quantity == 8
    assert page.items[0].reserved_quantity == 3
    assert page.next_cursor == "1"
    for call in connection.execute.call_args_list:
        assert call.args[1][0:2] == ("org-default", "store-1")
