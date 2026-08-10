import asyncio
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.product_offers import (
    PostgresProductOfferGateway,
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


def test_product_offer_query_is_tenant_scoped_and_preserves_money() -> None:
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = {"total": 2}
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = [
        {
            "offer_id": "SKU-1",
            "ozon_product_id": "10001",
            "name": "测试商品",
            "price_minor": 1234,
            "currency": "RUB",
            "available_stock": 5,
        }
    ]
    connection = MagicMock()
    connection.execute.side_effect = [count_cursor, rows_cursor]
    sessions = FakeSessions(connection)
    context = TenantContext("org-1", "user-1")
    gateway = PostgresProductOfferGateway(
        cast(PostgresSessionFactory, sessions),
        context,
    )

    page = asyncio.run(
        gateway.list_product_offers(workspace_id="workspace-1", cursor=None, limit=1)
    )

    assert sessions.received_context == context
    assert page.source == "postgresql"
    assert page.items[0].price.as_tuple().exponent == -2
    assert page.items[0].price == Decimal("12.34")
    assert page.next_cursor == "1"
    for call in connection.execute.call_args_list:
        assert call.args[1][0:2] == ("org-1", "workspace-1")
