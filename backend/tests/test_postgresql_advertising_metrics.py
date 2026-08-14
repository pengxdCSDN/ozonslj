import asyncio
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.domain.advertising_metrics import AdvertisingMetrics, calculate_advertising_metrics
from backend.app.infrastructure.postgresql.advertising_metrics import (
    PostgresAdvertisingMetricsGateway,
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


def test_metrics_snapshot_persists_inputs_and_derived_result() -> None:
    connection = MagicMock()
    sessions = FakeSessions(connection)
    context = TenantContext("org-1", "user-1")
    metrics = calculate_advertising_metrics(
        impressions=100, clicks=20, orders=3, ad_sales_minor=50000,
        total_sales_minor=70000, spend_minor=5000, currency="RUB", window="2026-08-01/2026-08-07",
    )
    gateway = PostgresAdvertisingMetricsGateway(cast(PostgresSessionFactory, sessions), context)

    result = asyncio.run(
        gateway.save_snapshot(
            workspace_id="workspace-1",
            inputs={"impressions": 100, "window": "2026-08-01/2026-08-07"},
            metrics=metrics,
        )
    )

    assert isinstance(result, AdvertisingMetrics)
    assert sessions.context == context
    query, params = connection.execute.call_args.args
    assert "advertising_metric_snapshots" in query
    assert "metric_window" in query
    assert params[1:3] == ("org-1", "workspace-1")
    assert '"impressions": 100' in params[5]
