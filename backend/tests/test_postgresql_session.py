from contextlib import nullcontext
from typing import cast
from unittest.mock import MagicMock

import pytest
from psycopg import Connection
from psycopg_pool import ConnectionPool

from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)


@pytest.mark.parametrize(
    ("organization_id", "user_id"),
    [("", "user-1"), ("org-1", " ")],
)
def test_tenant_context_rejects_empty_identifiers(
    organization_id: str,
    user_id: str,
) -> None:
    with pytest.raises(ValueError, match="不能为空"):
        TenantContext(organization_id=organization_id, user_id=user_id)


def test_transaction_sets_both_rls_values_before_business_sql() -> None:
    connection = MagicMock()
    connection.transaction.return_value = nullcontext()
    pool = MagicMock()
    pool.connection.return_value = nullcontext(connection)
    factory = PostgresSessionFactory(
        "postgresql://app:secret@postgres:5432/ozonslj",
        pool=cast(ConnectionPool[Connection[dict[str, object]]], pool),
    )

    with factory.transaction(TenantContext("org-1", "user-1")) as borrowed:
        assert borrowed is connection
        borrowed.execute("SELECT 1")

    first_call = connection.execute.call_args_list[0]
    assert "set_config('app.organization_id', %s, true)" in first_call.args[0]
    assert "set_config('app.user_id', %s, true)" in first_call.args[0]
    assert first_call.args[1] == ("org-1", "user-1")
    assert connection.execute.call_args_list[1].args == ("SELECT 1",)


def test_pool_lifecycle_is_explicit() -> None:
    pool = MagicMock()
    factory = PostgresSessionFactory(
        "postgresql://app:secret@postgres:5432/ozonslj",
        pool=cast(ConnectionPool[Connection[dict[str, object]]], pool),
    )

    factory.open()
    factory.close()

    pool.open.assert_called_once_with(wait=True)
    pool.close.assert_called_once_with()
