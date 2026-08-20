"""说明本模块的职责、边界和主要协作对象。"""

from uuid import uuid4

from backend.app.domain.seller_account import (
    CreatedSellerAccount,
    CredentialProtector,
    SellerAccountGateway,
    SellerCredentialVerifier,
)


class SellerAccountService:
    """验证并加密 Ozon 凭据，再原子创建卖家账号与工作区。"""

    def __init__(
        self,
        gateway: SellerAccountGateway,
        verifier: SellerCredentialVerifier,
        protector: CredentialProtector,
    ) -> None:
        """初始化对象依赖和运行时状态。"""
        self._gateway = gateway
        self._verifier = verifier
        self._protector = protector

    async def create(
        self,
        *,
        operator_id: str,
        display_name: str,
        workspace_name: str,
        client_id: str,
        api_key: str,
    ) -> CreatedSellerAccount:
        """执行 create 的业务流程并返回该流程的结果。"""
        normalized_client_id = client_id.strip()
        normalized_api_key = api_key.strip()
        await self._verifier.verify(client_id=normalized_client_id, api_key=normalized_api_key)
        encrypted_api_key = self._protector.encrypt(normalized_api_key)
        return await self._gateway.create(
            seller_account_id=f"seller_{uuid4().hex}",
            workspace_id=f"workspace_{uuid4().hex}",
            operator_id=operator_id,
            display_name=display_name.strip(),
            workspace_name=workspace_name.strip(),
            client_id=normalized_client_id,
            encrypted_api_key=encrypted_api_key,
            credential_version=self._protector.key_version,
        )
