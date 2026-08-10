import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.customer_orders import (
    PostgresCustomerOrderGateway,
)
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


def test_order_query_is_scoped_desensitized_and_preserves_money() -> None:
    now = datetime.now(UTC)
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = {"total": 2}
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = [
        {
            "id": "order-1",
            "ozon_order_id": "20001",
            "status": "delivered",
            "total_amount_minor": 123450,
            "currency": "RUB",
            "ordered_at": now,
            "synced_at": now,
        }
    ]
    connection = MagicMock()
    connection.execute.side_effect = [count_cursor, rows_cursor]
    sessions = FakeSessions(connection)
    context = TenantContext("org-default", "user-1")
    gateway = PostgresCustomerOrderGateway(
        cast(PostgresSessionFactory, sessions),
        context,
    )

    page = asyncio.run(
        gateway.list_customer_orders(workspace_id="store-1", cursor=None, limit=1)
    )

    assert sessions.received_context == context
    assert page.items[0].total_amount == Decimal("1234.50")
    assert page.items[0].total_amount.as_tuple().exponent == -2
    assert page.items[0].ordered_at == now
    assert page.next_cursor == "1"
    query_text = connection.execute.call_args_list[1].args[0]
    assert "raw_summary" not in query_text
    for call in connection.execute.call_args_list:
        assert call.args[1][0:2] == ("org-default", "store-1")
