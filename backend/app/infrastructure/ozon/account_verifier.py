"""说明本模块的职责、边界和主要协作对象。"""

from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from backend.app.domain.store_workspace import (
    OzonAuthenticationError,
    OzonCredentials,
    OzonMalformedResponseError,
    OzonPermissionError,
    OzonRateLimitError,
    OzonTemporaryError,
    SellerAccountVerifier,
)

_SELLER_INFO_PATH = "/v1/seller/info"
_JSON_OBJECT = TypeAdapter(dict[str, Any])


class StubSellerAccountVerifier(SellerAccountVerifier):
    """Stub 模式只验证本地输入边界，绝不访问真实 Ozon。"""

    async def verify(self, credentials: OzonCredentials) -> None:
        """执行 verify 的业务流程并返回该流程的结果。

Args:
    credentials: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    OzonAuthenticationError: 业务约束或外部依赖失败时抛出。
"""
        if not credentials.client_id.strip() or not credentials.api_key.strip():
            raise OzonAuthenticationError("Ozon 凭据不能为空")


class HttpOzonSellerAccountVerifier(SellerAccountVerifier):
    """通过 Ozon Seller API 的卖家信息只读操作验证凭据。"""

    def __init__(
        self,
        base_url: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """初始化对象依赖和运行时状态。

Args:
    base_url: 参数语义、输入边界和安全约束。
    transport: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    async def verify(self, credentials: OzonCredentials) -> None:
        """执行 verify 的业务流程并返回该流程的结果。

Args:
    credentials: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    OzonAuthenticationError: 业务约束或外部依赖失败时抛出。
    OzonPermissionError: 业务约束或外部依赖失败时抛出。
    OzonRateLimitError: 业务约束或外部依赖失败时抛出。
    OzonTemporaryError: 业务约束或外部依赖失败时抛出。
    OzonMalformedResponseError: 业务约束或外部依赖失败时抛出。
"""
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(10.0),
                transport=self._transport,
            ) as client:
                response = await client.get(
                    _SELLER_INFO_PATH,
                    headers={
                        "Client-Id": credentials.client_id,
                        "Api-Key": credentials.api_key,
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise OzonTemporaryError("暂时无法连接 Ozon，请稍后重试") from error

        if response.status_code == 401:
            raise OzonAuthenticationError("Ozon 拒绝了当前凭据")
        if response.status_code == 403:
            raise OzonPermissionError("当前凭据缺少卖家信息读取权限")
        if response.status_code == 429:
            raise OzonRateLimitError("Ozon 请求受限，请稍后重试")
        if response.status_code >= 500:
            raise OzonTemporaryError("Ozon 服务暂时不可用")
        if not response.is_success:
            raise OzonTemporaryError(f"Ozon 返回暂时性错误：HTTP {response.status_code}")

        try:
            payload = response.json()
            _JSON_OBJECT.validate_python(payload)
        except (ValueError, ValidationError) as error:
            raise OzonMalformedResponseError("Ozon 返回了无法识别的响应") from error
