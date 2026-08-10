from backend.app.api.dependencies import get_tenant_context
from backend.app.domain.identity import AuthenticatedUser


def test_verified_user_creates_immutable_database_context() -> None:
    user = AuthenticatedUser(
        id="user-1",
        email="owner@example.com",
        display_name="Owner",
        organization_id="org-1",
        organization_role="owner",
    )

    context = get_tenant_context(user)

    assert context.organization_id == "org-1"
    assert context.user_id == "user-1"
