"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


class SellerAccountConflictError(RuntimeError):
    """同一 Ozon Client-Id 已存在。"""


class SellerCredentialValidationError(RuntimeError):
    """Ozon 凭据验证失败，消息可安全返回给当前操作员。"""


@dataclass(frozen=True, slots=True)
class CreatedSellerAccount:
    """说明 CreatedSellerAccount 的职责、状态边界和对外协作关系。"""
    seller_account_id: str
    workspace_id: str
    display_name: str
    workspace_name: str
    status: str = "active"


class SellerCredentialVerifier(Protocol):
    """说明 SellerCredentialVerifier 的职责、状态边界和对外协作关系。"""
    async def verify(self, *, client_id: str, api_key: str) -> None:
        """执行 verify 的业务流程并返回该流程的结果。"""


class CredentialProtector(Protocol):
    """定义凭据保护器的密钥版本查询和加密接口。"""

    @property
    def key_version(self) -> int: """返回当前凭据保护密钥的版本。"""

    def encrypt(self, api_key: str) -> bytes: """加密 Api-Key，返回不可直接使用的密文。"""


class SellerAccountGateway(Protocol):
    """说明 SellerAccountGateway 的职责、状态边界和对外协作关系。"""
    async def create(
        self,
        *,
        seller_account_id: str,
        workspace_id: str,
        operator_id: str,
        display_name: str,
        workspace_name: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> CreatedSellerAccount:
        """执行 create 的业务流程并返回该流程的结果。"""
