"""说明本模块的职责、边界和主要协作对象。"""

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
OperatorRole = Literal["admin", "supervisor", "operator", "finance", "readonly_analyst"]


@dataclass(frozen=True, slots=True, init=False)
class AuthenticatedUser:
    """通过服务端会话验证且已选定活动组织的用户。"""

    id: str
    email: str
    display_name: str
    organization_id: str
    organization_role: OrganizationRole
    workspace_ids: tuple[str, ...]

    def __init__(
        self,
        *,
        id: str,
        email: str,
        display_name: str,
        organization_id: str = "org-default",
        organization_role: OrganizationRole | None = None,
        workspace_ids: tuple[str, ...] = (),
        role: str | None = None,
    ) -> None:
        """兼容旧的 role/workspace_ids 构造方式，同时保留组织级权限字段。

Args:
    id: 参数语义、输入边界和安全约束。
    email: 参数语义、输入边界和安全约束。
    display_name: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    organization_role: 参数语义、输入边界和安全约束。
    workspace_ids: 参数语义、输入边界和安全约束。
    role: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

        resolved_role = organization_role or role or "readonly_analyst"
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "email", email)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "organization_id", organization_id)
        object.__setattr__(self, "organization_role", resolved_role)
        object.__setattr__(self, "workspace_ids", workspace_ids)

    @property
    def role(self) -> str:
        """执行 role 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        return self.organization_role


@dataclass(frozen=True, slots=True)
class LoginResult:
    """说明 LoginResult 的职责、状态边界和对外协作关系。"""
    token: str
    expires_at: datetime
    user: AuthenticatedUser


class IdentityGateway(Protocol):
    """身份服务所需的最小 PostgreSQL 端口。"""

    async def find_login_identity(
        self,
        email: str,
        organization_id: str,
    ) -> tuple[AuthenticatedUser, str] | None:
        """执行 find_login_identity 的业务流程并返回该流程的结果。

Args:
    email: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def create_session(
        self,
        user_id: str,
        organization_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """执行 create_session 的业务流程并返回该流程的结果。

Args:
    user_id: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。
    token_hash: 参数语义、输入边界和安全约束。
    expires_at: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def find_user_by_session_hash(
        self,
        token_hash: str,
    ) -> AuthenticatedUser | None:
        """执行 find_user_by_session_hash 的业务流程并返回该流程的结果。

Args:
    token_hash: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def revoke_session(self, token_hash: str) -> None:
        """执行 revoke_session 的业务流程并返回该流程的结果。

Args:
    token_hash: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
