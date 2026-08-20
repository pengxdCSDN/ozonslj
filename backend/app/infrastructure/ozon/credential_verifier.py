"""说明本模块的职责、边界和主要协作对象。"""

import asyncio

from backend.app.domain.seller_account import SellerCredentialValidationError


class StubSellerCredentialVerifier:
    """Stub 模式只验证输入边界，不发起外部请求。"""

    async def verify(self, *, client_id: str, api_key: str) -> None:
        """执行 verify 的业务流程并返回该流程的结果。

Args:
    client_id: 参数语义、输入边界和安全约束。
    api_key: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    SellerCredentialValidationError: 业务约束或外部依赖失败时抛出。
"""
        await asyncio.sleep(0)
        if not client_id or not api_key:
            raise SellerCredentialValidationError("Ozon Client-Id 和 Api-Key 不能为空")


class LiveSellerCredentialVerifier:
    """官方验证端点完成复核前拒绝真实凭据接入。"""

    async def verify(self, *, client_id: str, api_key: str) -> None:
        """执行 verify 的业务流程并返回该流程的结果。

Args:
    client_id: 参数语义、输入边界和安全约束。
    api_key: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    SellerCredentialValidationError: 业务约束或外部依赖失败时抛出。
"""
        raise SellerCredentialValidationError("真实 Ozon 凭据验证尚未启用")
