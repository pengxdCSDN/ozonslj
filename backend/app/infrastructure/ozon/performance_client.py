from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx


class PerformanceTokenError(RuntimeError):
    """Performance Client Credentials 获取失败，错误信息不包含密钥内容。"""


async def request_performance_token(
    *, client_id: str, client_secret: str, timeout_seconds: float = 20.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[str, datetime]:
    """使用 Ozon Performance 服务账号获取短期访问令牌。"""
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, transport=transport) as client:
            response = await client.post(
                "https://performance.ozon.ru/api/client/token",
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
            )
    except httpx.HTTPError as error:
        raise PerformanceTokenError("Performance Token 请求失败") from error
    if response.status_code >= 400:
        raise PerformanceTokenError(
            f"Performance Token 获取失败（HTTP {response.status_code}）"
        )
    try:
        body: Any = response.json()
    except ValueError as error:
        raise PerformanceTokenError("Performance Token 响应不是合法 JSON") from error
    access_token = body.get("access_token") if isinstance(body, dict) else None
    expires_in = body.get("expires_in") if isinstance(body, dict) else None
    if not isinstance(access_token, str) or not access_token.strip():
        raise PerformanceTokenError("Performance Token 响应缺少 access_token")
    if not isinstance(expires_in, (int, float)) or expires_in <= 0:
        raise PerformanceTokenError("Performance Token 响应缺少有效 expires_in")
    return access_token, datetime.now(UTC) + timedelta(seconds=float(expires_in))
