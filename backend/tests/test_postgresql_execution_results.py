import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.domain.execution_result import BatchExecutionResult, ItemExecutionResult
from backend.app.infrastructure.postgresql.execution_results import PostgresExecutionResultGateway
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        del context
        yield self.connection


def test_save_execution_result_persists_item_level_outcomes() -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": "result-1", "workspace_id": "store-1",
        "result": {"total": 2, "succeeded": 1, "failed": 1, "status": "partial_failure",
                    "items": [{"item_id": "SKU-1", "success": True, "message": "完成"},
                              {"item_id": "SKU-2", "success": False, "message": "拒绝"}]},
        "created_at": datetime.now(UTC),
    }
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresExecutionResultGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "operator-1"),
    )

    stored = asyncio.run(gateway.save(
        workspace_id="store-1",
        result=BatchExecutionResult(
            2, 1, 1, "partial_failure",
            [
                ItemExecutionResult("SKU-1", True, "完成"),
                ItemExecutionResult("SKU-2", False, "拒绝"),
            ],
        ),
    ))

    assert stored.result.failed == 1
    assert len(stored.result.items) == 2
    sql, params = connection.execute.call_args.args
    assert "INSERT INTO execution_results" in sql
    assert params[1:3] == ("org-default", "store-1")
