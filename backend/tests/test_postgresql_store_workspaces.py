import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)
from backend.app.infrastructure.postgresql.store_workspaces import (
    PostgresStoreWorkspaceGateway,
)


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection
        self.contexts: list[TenantContext] = []

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        self.contexts.append(context)
        yield self.connection


def test_create_workspace_and_audit_share_tenant_scoped_transaction() -> None:
    now = datetime.now(UTC)
    empty_cursor = MagicMock()
    workspace_cursor = MagicMock()
    workspace_cursor.fetchone.return_value = {
        "id": "workspace-generated",
        "display_name": "俄罗斯主店",
        "status": "pending",
        "verified_at": None,
        "created_at": now,
        "updated_at": now,
    }
    connection = MagicMock()
    connection.execute.side_effect = [
        empty_cursor,
        empty_cursor,
        empty_cursor,
        workspace_cursor,
    ]
    sessions = FakeSessions(connection)
    context = TenantContext("org-1", "user-1")
    gateway = PostgresStoreWorkspaceGateway(
        cast(PostgresSessionFactory, sessions),
        context,
    )

    workspace = asyncio.run(
        gateway.create_workspace(
            display_name="俄罗斯主店",
            client_id="client-1",
            encrypted_api_key=b"ciphertext",
            credential_version=7,
        )
    )

    assert workspace.status == "pending"
    assert sessions.contexts == [context, context]
    account_params = connection.execute.call_args_list[0].args[1]
    workspace_params = connection.execute.call_args_list[1].args[1]
    audit_params = connection.execute.call_args_list[2].args[1]
    assert account_params[1] == "org-1"
    assert account_params[5] == 7
    assert workspace_params[1] == "org-1"
    assert audit_params[1:4] == ("org-1", workspace_params[0], "user-1")
    assert b"ciphertext" not in audit_params


def test_list_workspaces_always_filters_current_organization() -> None:
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    connection = MagicMock()
    connection.execute.return_value = cursor
    sessions = FakeSessions(connection)
    gateway = PostgresStoreWorkspaceGateway(
        cast(PostgresSessionFactory, sessions),
        TenantContext("org-2", "user-2"),
    )

    workspaces = asyncio.run(gateway.list_workspaces())

    assert workspaces == []
    assert connection.execute.call_args.args[1] == ("org-2",)
