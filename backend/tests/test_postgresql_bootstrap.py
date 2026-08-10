from typing import cast
from unittest.mock import MagicMock

import pytest
from psycopg import Connection

from backend.app.infrastructure.postgresql.bootstrap import (
    BootstrapRoleRequiredError,
    provision_organization_owner,
)


def test_normal_application_role_cannot_bootstrap_owner() -> None:
    role_cursor = MagicMock()
    role_cursor.fetchone.return_value = (False, False)
    connection = MagicMock()
    connection.execute.return_value = role_cursor

    with pytest.raises(BootstrapRoleRequiredError, match="BYPASSRLS"):
        provision_organization_owner(
            cast(Connection[tuple[object, ...]], connection),
            organization_id="org-1",
            organization_name="组织一",
            email="owner@example.com",
            display_name="Owner",
            password_hash="scrypt$hash",
        )

    connection.transaction.assert_not_called()


def test_bootstrap_upserts_owner_and_revokes_existing_sessions() -> None:
    role_cursor = MagicMock()
    role_cursor.fetchone.return_value = (False, True)
    user_cursor = MagicMock()
    user_cursor.fetchone.return_value = ("user-1",)
    connection = MagicMock()
    connection.execute.side_effect = [
        role_cursor,
        MagicMock(),
        user_cursor,
        MagicMock(),
        MagicMock(),
        MagicMock(),
    ]

    user_id = provision_organization_owner(
        cast(Connection[tuple[object, ...]], connection),
        organization_id="org-1",
        organization_name="组织一",
        email="OWNER@EXAMPLE.COM",
        display_name="Owner",
        password_hash="scrypt$hash",
    )

    assert user_id == "user-1"
    assert connection.execute.call_args_list[2].args[1] == ("owner@example.com",)
    assert "UPDATE user_sessions" in connection.execute.call_args_list[-1].args[0]
