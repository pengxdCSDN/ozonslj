import pytest
from fastapi import HTTPException

from backend.app.api.dependencies import require_account_manager
from backend.app.domain.identity import AuthenticatedUser, OrganizationRole


def _user(role: OrganizationRole) -> AuthenticatedUser:
    return AuthenticatedUser(
        id="user-1",
        email="user@example.com",
        display_name="User",
        organization_id="org-1",
        organization_role=role,
    )


@pytest.mark.parametrize("role", ["owner", "admin"])
def test_owner_and_admin_can_manage_seller_accounts(role: OrganizationRole) -> None:
    user = _user(role)

    assert require_account_manager(user) is user


@pytest.mark.parametrize(
    "role",
    ["operations_manager", "operator", "finance", "readonly_analyst"],
)
def test_non_admin_roles_cannot_manage_seller_credentials(role: OrganizationRole) -> None:
    with pytest.raises(HTTPException) as captured:
        require_account_manager(_user(role))

    assert captured.value.status_code == 403
    assert captured.value.detail["code"] == "insufficient_role"
