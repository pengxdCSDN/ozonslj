import asyncio

from backend.app.domain.seller_account import SellerCredentialValidationError


class StubSellerCredentialVerifier:
    """Stub 模式只验证输入边界，不发起外部请求。"""

    async def verify(self, *, client_id: str, api_key: str) -> None:
        await asyncio.sleep(0)
        if not client_id or not api_key:
            raise SellerCredentialValidationError("Ozon Client-Id 和 Api-Key 不能为空")


class LiveSellerCredentialVerifier:
    """官方验证端点完成复核前拒绝真实凭据接入。"""

    async def verify(self, *, client_id: str, api_key: str) -> None:
        raise SellerCredentialValidationError("真实 Ozon 凭据验证尚未启用")
