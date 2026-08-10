import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.seller_operations import (
    PostgresSellerOperationGateway,
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


def test_operation_query_is_scoped_and_excludes_sensitive_columns() -> None:
    occurred_at = datetime.now(UTC)
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = {"total": 2}
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = [
        {
            "id": "operation-1",
            "operation_type": "stock_sync",
            "risk_level": "read",
            "target_type": "stock_position",
            "target_count": 25,
            "request_id": "request-1",
            "result": "success",
            "occurred_at": occurred_at,
        }
    ]
    connection = MagicMock()
    connection.execute.side_effect = [count_cursor, rows_cursor]
    sessions = FakeSessions(connection)
    context = TenantContext("org-default", "user-1")
    gateway = PostgresSellerOperationGateway(
        cast(PostgresSessionFactory, sessions),
        context,
    )

    page = asyncio.run(
        gateway.list_seller_operations(workspace_id="store-1", cursor=None, limit=1)
    )

    assert sessions.received_context == context
    assert page.items[0].operation_type == "stock_sync"
    assert page.items[0].occurred_at == occurred_at
    assert page.next_cursor == "1"
    query_text = connection.execute.call_args_list[1].args[0]
    for forbidden_column in ("detail", "operator_id", "user_id"):
        assert forbidden_column not in query_text
    for call in connection.execute.call_args_list:
        assert call.args[1][0:2] == ("org-default", "store-1")
