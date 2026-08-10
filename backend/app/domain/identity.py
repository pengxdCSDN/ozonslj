from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

OrganizationRole = Literal[
    "owner",
    "admin",
    "operations_manager",
    "operator",
    "finance",
    "readonly_analyst",
]


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """通过服务端会话验证且已选定活动组织的用户。"""

    id: str
    email: str
    display_name: str
    organization_id: str
    organization_role: OrganizationRole


@dataclass(frozen=True, slots=True)
class LoginResult:
    token: str
    expires_at: datetime
    user: AuthenticatedUser


class IdentityGateway(Protocol):
    """身份服务所需的最小 PostgreSQL 端口。"""

    async def find_login_identity(
        self,
        email: str,
        organization_id: str,
    ) -> tuple[AuthenticatedUser, str] | None: ...

    async def create_session(
        self,
        user_id: str,
        organization_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None: ...

    async def find_user_by_session_hash(
        self,
        token_hash: str,
    ) -> AuthenticatedUser | None: ...

    async def revoke_session(self, token_hash: str) -> None: ...
