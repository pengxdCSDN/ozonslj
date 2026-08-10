import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.domain.sync_job import SyncJobPage
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext
from backend.app.infrastructure.postgresql.sync_jobs import PostgresSyncJobGateway


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        del context
        yield self.connection


def test_create_job_uses_idempotency_and_context() -> None:
    now = datetime.now(UTC)
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "id": "sync-1", "workspace_id": "store-1", "resource_type": "stock",
        "status": "queued", "processed_count": 0, "failure_count": 0,
        "error_code": None, "error_message": None, "attempt_count": 0,
        "max_attempts": 3, "next_attempt_at": now, "created_at": now,
        "started_at": None, "completed_at": None, "lease_owner": None,
        "lease_expires_at": None, "heartbeat_at": None,
    }
    connection = MagicMock()
    connection.execute.return_value = cursor
    gateway = PostgresSyncJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "user-1"),
    )

    job = asyncio.run(gateway.create_sync_job(
        workspace_id="store-1", resource_type="stock", idempotency_key="stock-sync-001"
    ))

    assert job.id == "sync-1"
    sql, params = connection.execute.call_args.args
    assert "ON CONFLICT" in sql
    assert params[1:] == ("org-default", "store-1", "stock", "user-1", "stock-sync-001")


def test_dispatch_scan_reads_only_due_queued_jobs() -> None:
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    connection.execute.return_value = cursor
    gateway = PostgresSyncJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "scheduler-user"),
    )

    jobs = asyncio.run(gateway.list_dispatchable_sync_jobs(limit=50))

    assert jobs == []
    sql, params = connection.execute.call_args.args
    assert "status = 'queued'" in sql
    assert "next_attempt_at <= CURRENT_TIMESTAMP" in sql
    assert params == ("org-default", 50)


def test_list_jobs_uses_workspace_scope_and_stable_offset_cursor() -> None:
    now = datetime.now(UTC)
    row = {
        "id": "sync-1", "workspace_id": "store-1", "resource_type": "stock",
        "status": "succeeded", "processed_count": 2, "failure_count": 0,
        "error_code": None, "error_message": None, "attempt_count": 1,
        "max_attempts": 3, "next_attempt_at": now, "created_at": now,
        "started_at": now, "completed_at": now, "lease_owner": None,
        "lease_expires_at": None, "heartbeat_at": now,
    }
    connection = MagicMock()
    total_cursor = MagicMock()
    total_cursor.fetchone.return_value = {"total": 3}
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = [row]
    connection.execute.side_effect = [total_cursor, rows_cursor]
    gateway = PostgresSyncJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "operator-1"),
    )

    page = asyncio.run(gateway.list_sync_jobs(workspace_id="store-1", cursor="1", limit=1))

    assert isinstance(page, SyncJobPage)
    assert page.next_cursor == "2"
    assert page.items[0].status == "succeeded"
    sql, params = connection.execute.call_args_list[1].args
    assert "ORDER BY created_at DESC, id DESC" in sql
    assert params == ("org-default", "store-1", 1, 1)


def test_cancel_only_updates_queued_or_running_task() -> None:
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": "sync-1"}
    connection.execute.return_value = cursor
    gateway = PostgresSyncJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "operator-1"),
    )

    assert asyncio.run(gateway.request_cancel_sync_job(job_id="sync-1")) is True
    sql, params = connection.execute.call_args.args
    assert "status IN ('queued', 'running')" in sql
    assert params == ("org-default", "sync-1")


def test_retry_only_requeues_failed_or_partial_task() -> None:
    now = datetime.now(UTC)
    row = {
        "id": "sync-1", "workspace_id": "store-1", "resource_type": "stock",
        "status": "queued", "processed_count": 1, "failure_count": 1,
        "error_code": None, "error_message": None, "attempt_count": 2,
        "max_attempts": 3, "next_attempt_at": now, "created_at": now,
        "started_at": now, "completed_at": None, "lease_owner": None,
        "lease_expires_at": None, "heartbeat_at": now,
    }
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    connection.execute.return_value = cursor
    gateway = PostgresSyncJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "operator-1"),
    )

    retried = asyncio.run(gateway.retry_sync_job(job_id="sync-1"))

    assert retried is not None
    assert retried.status == "queued"
    sql, params = connection.execute.call_args.args
    assert "status IN ('failed', 'partial')" in sql
    assert params == ("org-default", "sync-1")


def test_claim_job_is_atomic_and_recovers_expired_lease() -> None:
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    connection.execute.return_value = cursor
    gateway = PostgresSyncJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "worker-user"),
    )

    claimed = asyncio.run(
        gateway.claim_sync_job(job_id="sync-1", worker_id="worker-1", lease_seconds=30)
    )

    assert claimed is None
    sql, params = connection.execute.call_args.args
    assert "attempt_count = attempt_count + 1" in sql
    assert "lease_expires_at < CURRENT_TIMESTAMP" in sql
    assert params[0] == "worker-1"
    assert params[2:] == ("org-default", "sync-1")


def test_heartbeat_and_complete_require_current_lease_owner() -> None:
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": "sync-1"}
    connection.execute.return_value = cursor
    gateway = PostgresSyncJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "worker-user"),
    )

    heartbeat = asyncio.run(
        gateway.heartbeat_sync_job(job_id="sync-1", worker_id="worker-1", lease_seconds=30)
    )
    completed = asyncio.run(
        gateway.complete_sync_job(
            job_id="sync-1", worker_id="worker-1", processed_count=10, failure_count=0
        )
    )

    assert heartbeat is True
    assert completed is True
    for call in connection.execute.call_args_list:
        assert "lease_owner = %s" in call.args[0]
        assert "lease_expires_at >= CURRENT_TIMESTAMP" in call.args[0]


def test_failure_requeues_until_max_attempts_then_stops() -> None:
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": "sync-1"}
    connection.execute.return_value = cursor
    gateway = PostgresSyncJobGateway(
        cast(PostgresSessionFactory, FakeSessions(connection)),
        TenantContext("org-default", "worker-user"),
    )

    failed = asyncio.run(
        gateway.fail_sync_job(
            job_id="sync-1", worker_id="worker-1", error_code="upstream_timeout",
            error_message="上游读取超时", retry_delay_seconds=60,
        )
    )

    assert failed is True
    sql = connection.execute.call_args.args[0]
    assert "attempt_count >= max_attempts THEN 'failed'" in sql
    assert "ELSE 'queued'" in sql
