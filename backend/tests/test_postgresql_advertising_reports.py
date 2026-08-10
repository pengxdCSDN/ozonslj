import asyncio
from contextlib import contextmanager
from datetime import date
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.domain.advertising_report import AdvertisingReportRow
from backend.app.infrastructure.postgresql.advertising_reports import (
    PostgresAdvertisingReportGateway,
)
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection
        self.context: TenantContext | None = None

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        self.context = context
        yield self.connection


def test_report_save_uses_idempotent_workspace_scoped_key() -> None:
    connection = MagicMock()
    sessions = FakeSessions(connection)
    context = TenantContext("org-1", "user-1")
    row = AdvertisingReportRow("campaign-1", date(2026, 8, 1), 100, 20, 3, 50000, 5000, "RUB")
    gateway = PostgresAdvertisingReportGateway(cast(PostgresSessionFactory, sessions), context)

    result = asyncio.run(gateway.save_rows(workspace_id="workspace-1", rows=[row]))

    assert result == [row]
    assert sessions.context == context
    query, params = connection.execute.call_args.args
    assert "ON CONFLICT" in query
    assert params[1:4] == ("org-1", "workspace-1", "campaign-1")
