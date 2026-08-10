import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.infrastructure.postgresql.identity import PostgresIdentityGateway
from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection
        self.tenant_contexts: list[TenantContext] = []

    @contextmanager
    def authentication_transaction(self) -> Any:
        yield self.connection

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        self.tenant_contexts.append(context)
        yield self.connection


def test_login_lookup_sets_rls_context_before_membership_query() -> None:
    user_cursor = MagicMock()
    user_cursor.fetchone.return_value = {
        "id": "user-1",
        "email": "owner@example.com",
        "display_name": "Owner",
        "password_hash": "scrypt$hash",
    }
    context_cursor = MagicMock()
    member_cursor = MagicMock()
    member_cursor.fetchone.return_value = {"role": "owner"}
    connection = MagicMock()
    connection.execute.side_effect = [user_cursor, context_cursor, member_cursor]
    gateway = PostgresIdentityGateway(
        cast(PostgresSessionFactory, FakeSessions(connection))
    )

    result = asyncio.run(
        gateway.find_login_identity("owner@example.com", "org-1")
    )

    assert result is not None
    assert result[0].organization_id == "org-1"
    assert result[0].organization_role == "owner"
    assert "set_config('app.organization_id'" in connection.execute.call_args_list[1].args[0]
    assert connection.execute.call_args_list[1].args[1] == ("org-1", "user-1")
    assert connection.execute.call_args_list[2].args[1] == ("org-1", "user-1")


def test_create_session_uses_tenant_transaction_and_hash_only() -> None:
    connection = MagicMock()
    sessions = FakeSessions(connection)
    gateway = PostgresIdentityGateway(cast(PostgresSessionFactory, sessions))
    token_hash = "a" * 64

    asyncio.run(
        gateway.create_session(
            "user-1",
            "org-1",
            token_hash,
            datetime.now(UTC),
        )
    )

    assert sessions.tenant_contexts == [TenantContext("org-1", "user-1")]
    insert_call = connection.execute.call_args_list[1]
    assert token_hash in insert_call.args[1]
    assert all("raw-token" not in str(call) for call in connection.execute.call_args_list)
