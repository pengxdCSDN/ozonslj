import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.domain.audit_event import AuditEvent
from backend.app.infrastructure.postgresql.audit_events import PostgresAuditEventGateway
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        del context
        yield self.connection


def test_save_audit_event_persists_lifecycle_stage_and_subject() -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": "event-1", "workspace_id": "store-1", "event_type": "readback_verified",
        "subject_id": "price-change-1", "detail": {"matched": True},
        "occurred_at": datetime.now(UTC),
    }
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresAuditEventGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "operator-1"),
    )
    stored = asyncio.run(gateway.save(
        workspace_id="store-1",
        event=AuditEvent(
            "readback_verified", "price-change-1", {"matched": True}, datetime.now(UTC)
        ),
    ))
    assert stored.event.event_type == "readback_verified"
    assert stored.event.detail["matched"] is True
    assert "INSERT INTO audit_events" in connection.execute.call_args.args[0]
