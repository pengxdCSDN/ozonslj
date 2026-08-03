from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

OperatorRole = Literal["admin", "supervisor", "operator", "finance", "readonly_analyst"]


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: str
    email: str
    display_name: str
    role: OperatorRole
    workspace_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoginResult:
    token: str
    expires_at: datetime
    user: AuthenticatedUser


class IdentityGateway(Protocol):
    async def find_login_identity(self, email: str) -> tuple[AuthenticatedUser, str] | None: ...

    async def create_session(
        self, operator_id: str, token_hash: str, expires_at: datetime
    ) -> None: ...

    async def find_user_by_session_hash(self, token_hash: str) -> AuthenticatedUser | None: ...

    async def revoke_session(self, token_hash: str) -> None: ...
