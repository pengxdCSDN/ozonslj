import asyncio
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.model_adapters import PostgresModelAdapterGateway
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection
        self.context: TenantContext | None = None

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        self.context = context
        yield self.connection


def test_active_model_adapter_query_is_workspace_scoped_and_secret_free() -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "adapter": "generic", "provider": "Local", "model": "stub",
        "base_url": "http://localhost:8000/v1", "enabled": True,
        "credential_configured": False,
    }
    connection = MagicMock()
    connection.execute.return_value = cursor
    sessions = FakeSessions(connection)
    gateway = PostgresModelAdapterGateway(
        cast(PostgresSessionFactory, sessions), TenantContext("org-1", "user-1")
    )

    result = asyncio.run(gateway.get_active_config(workspace_id="workspace-1"))

    assert result is not None
    assert result.enabled is True
    assert not hasattr(result, "api_key")
    assert sessions.context == TenantContext("org-1", "user-1")
    assert connection.execute.call_args.args[1] == ("org-1", "workspace-1")
