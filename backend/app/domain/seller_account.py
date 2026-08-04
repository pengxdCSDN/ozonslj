from dataclasses import dataclass
from typing import Protocol


class SellerAccountConflictError(RuntimeError):
    """同一 Ozon Client-Id 已存在。"""


class SellerCredentialValidationError(RuntimeError):
    """Ozon 凭据验证失败，消息可安全返回给当前操作员。"""


@dataclass(frozen=True, slots=True)
class CreatedSellerAccount:
    seller_account_id: str
    workspace_id: str
    display_name: str
    workspace_name: str
    status: str = "active"


class SellerCredentialVerifier(Protocol):
    async def verify(self, *, client_id: str, api_key: str) -> None: ...


class CredentialProtector(Protocol):
    @property
    def key_version(self) -> int: ...

    def encrypt(self, api_key: str) -> bytes: ...


class SellerAccountGateway(Protocol):
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
    ) -> CreatedSellerAccount: ...
