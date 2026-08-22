"""质量检查任务 PostgreSQL 幂等适配器测试。"""

import asyncio
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.quality_check_jobs import PostgresQualityCheckJobGateway
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        del context
        yield self.connection


def test_quality_check_job_insert_is_idempotent() -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": "quality-1"}
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresQualityCheckJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-1", "worker-1"),
    )

    assert asyncio.run(gateway.schedule_quality_check(
        workspace_id="workspace-1", data_version="v1",
        idempotency_key="workspace-1:run-1:quality_check:v1", parent_run_id="run-1",
    )) is True
    sql, params = connection.execute.call_args.args
    assert "ON CONFLICT" in sql
    assert "DO NOTHING" in sql
    assert params[1:] == (
        "org-1", "workspace-1", "v1", "workspace-1:run-1:quality_check:v1", "run-1"
    )


def test_duplicate_quality_check_returns_false() -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresQualityCheckJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-1", "worker-1"),
    )

    assert asyncio.run(gateway.schedule_quality_check(
        workspace_id="workspace-1", data_version="v1", idempotency_key="same",
        parent_run_id="run-1",
    )) is False
