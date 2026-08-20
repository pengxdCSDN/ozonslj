"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, SecretStr

StoreWorkspaceStatus = Literal["pending", "active", "invalid", "disabled"]


class StoreWorkspace(BaseModel):
    """返回给扩展的脱敏工作区视图。"""

    model_config = ConfigDict(frozen=True)

    id: str
    display_name: str
    status: StoreWorkspaceStatus
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WorkspaceNotFoundError(LookupError):
    """请求的卖家工作区不存在或不属于当前部署的数据边界。"""


class CreateStoreWorkspace(BaseModel):
    """创建卖家工作区时接收的凭据，不允许额外字段绕过接口边界。"""

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    client_id: str = Field(min_length=1, max_length=120)
    api_key: SecretStr = Field(min_length=1, max_length=1024)


class ReplaceStoreCredentials(BaseModel):
    """替换凭据后，工作区必须重新完成独立验证。"""

    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1, max_length=120)
    api_key: SecretStr = Field(min_length=1, max_length=1024)


@dataclass(frozen=True, slots=True)
class OzonCredentials:
    """仅在后端进程内短暂存在的 Ozon 认证材料。"""

    client_id: str
    api_key: str = field(repr=False)


class CredentialProtector(Protocol):
    """隔离版本化凭据保护能力，测试可以替换为内存实现。"""

    @property
    def key_version(self) -> int:
        """执行 key_version 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
    def protect(self, plaintext: str) -> bytes:
        """执行 protect 的业务流程并返回该流程的结果。

Args:
    plaintext: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    def unprotect(self, ciphertext: bytes, *, credential_version: int) -> str:
        """执行 unprotect 的业务流程并返回该流程的结果。

Args:
    ciphertext: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class StoreWorkspaceGateway(Protocol):
    """定义账户与工作区持久化所需的最小端口。"""

    async def list_workspaces(self) -> list[StoreWorkspace]:
        """执行 list_workspaces 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""

    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        """执行 get_workspace 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def create_workspace(
        self,
        *,
        display_name: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> StoreWorkspace:
        """执行 create_workspace 的业务流程并返回该流程的结果。

Args:
    display_name: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    encrypted_api_key: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def replace_credentials(
        self,
        *,
        workspace_id: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> StoreWorkspace | None:
        """执行 replace_credentials 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    encrypted_api_key: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def load_credentials(
        self,
        workspace_id: str,
    ) -> tuple[str, bytes, int] | None:
        """执行 load_credentials 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def set_verification_status(
        self,
        *,
        workspace_id: str,
        status: StoreWorkspaceStatus,
        verified_at: datetime | None,
        audit_result: Literal["success", "failed"],
        audit_detail: dict[str, str] | None = None,
    ) -> StoreWorkspace | None:
        """执行 set_verification_status 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。
    verified_at: 参数语义、输入边界和安全约束。
    audit_result: 参数语义、输入边界和安全约束。
    audit_detail: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class SellerAccountVerifier(Protocol):
    """验证凭据能否访问当前卖家账户，不向调用方泄漏原始响应。"""

    async def verify(self, credentials: OzonCredentials) -> None:
        """执行 verify 的业务流程并返回该流程的结果。

Args:
    credentials: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class CredentialProtectionError(RuntimeError):
    """凭据密文损坏、归属用户不匹配或系统保护失败。"""


class UnsupportedCredentialVersionError(CredentialProtectionError):
    """数据库中的凭据版本不受当前运行时支持。"""


class ClientIdConflictError(RuntimeError):
    """Client ID 已被另一个本地卖家账户占用。"""


class SellerVerificationError(RuntimeError):
    """Ozon 凭据验证失败的统一基类。"""


class OzonAuthenticationError(SellerVerificationError):
    """Ozon 拒绝了 Client ID 或 API Key。"""


class OzonPermissionError(SellerVerificationError):
    """凭据有效，但缺少验证操作所需权限。"""


class OzonRateLimitError(SellerVerificationError):
    """Ozon 对验证操作执行了限流。"""


class OzonTemporaryError(SellerVerificationError):
    """网络、超时或服务端错误允许稍后重试。"""


class OzonMalformedResponseError(SellerVerificationError):
    """Ozon 返回成功状态但响应结构无法识别。"""
