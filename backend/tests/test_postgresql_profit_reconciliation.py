import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.app.domain.profit_reconciliation_record import ProfitReconciliationRecord
from backend.app.infrastructure.postgresql.profit_reconciliation import (
    PostgresProfitReconciliationGateway,
)
from backend.app.infrastructure.postgresql.session import TenantContext


def test_reconciliation_gateway_reuses_idempotent_batch() -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": "batch-1",
        "workspace_id": "workspace-1",
        "idempotency_key": "key-1",
        "source": "ozon",
        "status": "completed",
        "created_at": datetime.now(UTC),
    }
    connection = MagicMock()
    connection.execute.return_value = cursor
    sessions = MagicMock()
    transaction = MagicMock()
    transaction.__enter__.return_value = connection
    transaction.__exit__.return_value = False
    sessions.transaction.return_value = transaction
    gateway = PostgresProfitReconciliationGateway(sessions, TenantContext("org-1", "worker"))
    batch = asyncio.run(
        gateway.create_batch(
            workspace_id="workspace-1",
            idempotency_key="key-1",
            source="ozon",
            status="completed",
            records=[],
        )
    )
    assert batch.id == "batch-1"
    assert connection.execute.call_count == 1


def test_reconciliation_record_keeps_missing_side() -> None:
    record = ProfitReconciliationRecord(
        id="record-1",
        batch_id="batch-1",
        workspace_id="workspace-1",
        order_id="o-1",
        sku_id="s-1",
        estimated_profit_minor=None,
        actual_profit_minor=800,
        variance_minor=None,
        side="missing_estimated",
        source="ozon",
        created_at=datetime.now(UTC),
    )
    assert record.side == "missing_estimated"
