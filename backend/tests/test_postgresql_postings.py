import asyncio
from contextlib import contextmanager
from datetime import UTC, date, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.postings import PostgresPostingGateway
from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection
        self.received_context: TenantContext | None = None

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        self.received_context = context
        yield self.connection


def test_posting_query_is_scoped_aggregated_and_desensitized() -> None:
    now = datetime.now(UTC)
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = {"total": 2}
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = [
        {
            "id": "posting-1",
            "customer_order_id": "order-1",
            "ozon_posting_number": "FBS-20001",
            "fulfillment_type": "FBS",
            "status": "awaiting_deliver",
            "shipment_date": date(2026, 8, 8),
            "synced_at": now,
            "item_count": 2,
            "total_quantity": 4,
        }
    ]
    connection = MagicMock()
    connection.execute.side_effect = [count_cursor, rows_cursor]
    sessions = FakeSessions(connection)
    context = TenantContext("org-default", "user-1")
    gateway = PostgresPostingGateway(cast(PostgresSessionFactory, sessions), context)

    page = asyncio.run(gateway.list_postings(workspace_id="store-1", cursor=None, limit=1))

    assert sessions.received_context == context
    assert page.items[0].fulfillment_type == "FBS"
    assert page.items[0].item_count == 2
    assert page.items[0].total_quantity == 4
    assert page.next_cursor == "1"
    query_text = connection.execute.call_args_list[1].args[0]
    assert "tracking_number" not in query_text
    for call in connection.execute.call_args_list:
        assert call.args[1][0:2] == ("org-default", "store-1")
