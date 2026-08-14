import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.domain.readback_verification import ReadbackField, ReadbackVerification
from backend.app.infrastructure.postgresql.readback_verifications import (
    PostgresReadbackVerificationGateway,
)
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        del context
        yield self.connection


def test_save_readback_keeps_field_level_difference() -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": "readback-1", "workspace_id": "store-1",
        "verification": {
            "matched": False, "message": "回读核对发现差异",
            "fields": [{"field": "price", "expected": "100", "actual": "110", "matched": False}],
        },
        "created_at": datetime.now(UTC),
    }
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresReadbackVerificationGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "operator-1"),
    )

    stored = asyncio.run(gateway.save(
        workspace_id="store-1",
        verification=ReadbackVerification(
            False, [ReadbackField("price", "100", "110", False)], "回读核对发现差异"
        ),
    ))

    assert stored.verification.matched is False
    assert stored.verification.fields[0].actual == "110"
    assert "INSERT INTO readback_verifications" in connection.execute.call_args.args[0]
