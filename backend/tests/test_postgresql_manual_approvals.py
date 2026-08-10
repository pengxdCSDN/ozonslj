import asyncio
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.manual_approvals import PostgresManualApprovalGateway
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        del context
        yield self.connection


def test_repeated_approval_creation_returns_existing_row_from_upsert() -> None:
    row = {
        "approval_id": "approval-1", "workspace_id": "store-1", "command_type": "price",
        "payload": {"sku": "sku-1"}, "status": "pending", "reviewer": None,
        "idempotency_key": "price-approval-001",
    }
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresManualApprovalGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "operator-1"),
    )

    approval = asyncio.run(gateway.create(
        workspace_id="store-1", command_type="price", payload={"sku": "sku-1"},
        idempotency_key="price-approval-001",
    ))

    assert approval.approval_id == "approval-1"
    sql, params = connection.execute.call_args.args
    assert "ON CONFLICT (organization_id, workspace_id, idempotency_key)" in sql
    assert "DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key" in sql
    assert "RETURNING approval_id" in sql
    assert params[-1] == "price-approval-001"


def test_approve_returns_idempotency_key_for_auditable_result() -> None:
    cursor = MagicMock()
    cursor.fetchall.return_value = [{
        "approval_id": "approval-1", "workspace_id": "store-1", "command_type": "price",
        "payload": {"sku": "sku-1"}, "status": "approved", "reviewer": "operator-1",
        "idempotency_key": "price-approval-001",
    }]
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresManualApprovalGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "operator-1"),
    )

    approval = asyncio.run(gateway.approve(approval_id="approval-1", reviewer="operator-1"))

    assert approval is not None
    assert approval.idempotency_key == "price-approval-001"
    assert "idempotency_key" in connection.execute.call_args.args[0]
