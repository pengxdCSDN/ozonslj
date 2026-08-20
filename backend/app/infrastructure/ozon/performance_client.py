"""说明本模块的职责、边界和主要协作对象。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

# Performance 接口必须使用 API 专用域名。performance.ozon.ru 是网页入口，
# 会返回面向浏览器的重定向或 HTML，不能用于携带服务账号密钥的后端调用。
PERFORMANCE_API_HOST = "api-performance.ozon.ru"
PERFORMANCE_TOKEN_URL = httpx.URL(
    f"https://{PERFORMANCE_API_HOST}/api/client/token"
)
PERFORMANCE_CAMPAIGNS_URL = httpx.URL(
    f"https://{PERFORMANCE_API_HOST}/api/client/campaign"
)


class PerformanceTokenError(RuntimeError):
    """Performance Client Credentials 获取失败，错误信息不包含密钥内容。"""

    def __init__(
        self, message: str, *, code: str = "performance_token_request_failed"
    ) -> None:
        """初始化对象依赖和运行时状态。"""
        super().__init__(message)
        self.code = code


def _content_type(response: httpx.Response) -> str:
    """只返回响应头中的媒体类型，避免把上游响应正文带入错误信息。"""
    return response.headers.get("content-type", "").split(";", 1)[0].strip() or "未返回"


def _token_http_error(response: httpx.Response) -> PerformanceTokenError:
    """将 OAuth 上游状态转换为可操作且不泄露正文的错误。"""
    status = response.status_code
    if status == 401:
        return PerformanceTokenError(
            "Performance 凭据校验失败（HTTP 401）：请确认 Client ID 和 "
            "Client Secret 属于 Performance 服务账号。",
            code="performance_oauth_invalid",
        )
    if status == 403:
        return PerformanceTokenError(
            "Performance 凭据无权访问（HTTP 403）：请确认账号已开通广告/Performance 权限。",
            code="performance_permission_denied",
        )
    if status == 429:
        return PerformanceTokenError(
            "Performance 请求受限（HTTP 429）：请稍后重试，避免重复点击。",
            code="performance_rate_limited",
        )
    if status >= 500:
        return PerformanceTokenError(
            f"Performance 服务暂时不可用（HTTP {status}）。",
            code="performance_upstream_unavailable",
        )
    return PerformanceTokenError(
        f"Performance Token 获取失败（HTTP {status}）。",
        code="performance_token_request_failed",
    )


async def request_performance_token(
    *, client_id: str, client_secret: str, timeout_seconds: float = 20.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[str, datetime]:
    """使用 Ozon Performance 服务账号获取短期访问令牌。"""
    token_url = PERFORMANCE_TOKEN_URL
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds, transport=transport, follow_redirects=False
        ) as client:
            response = await client.post(token_url, json=payload)
            for _ in range(3):
                if response.status_code not in {301, 302, 303, 307, 308}:
                    break
                location = response.headers.get("location")
                if not location:
                    raise PerformanceTokenError(
                        "Performance Token 重定向缺少目标地址。",
                        code="performance_upstream_redirect",
                    )
                redirect_url = token_url.join(location)
                if (
                    redirect_url.scheme != "https"
                    or redirect_url.host != PERFORMANCE_API_HOST
                    or redirect_url.port not in {None, 443}
                ):
                    raise PerformanceTokenError(
                        "Performance Token 重定向目标不受信任，已阻止提交凭据。",
                        code="performance_upstream_redirect",
                    )
                token_url = redirect_url
                response = await client.post(token_url, json=payload)
            else:
                raise PerformanceTokenError(
                    "Performance Token 重定向次数过多。",
                    code="performance_upstream_redirect",
                )
    except httpx.TimeoutException as error:
        raise PerformanceTokenError(
            "Performance Token 请求超时：请检查网络后稍后重试。", code="performance_timeout"
        ) from error
    except httpx.HTTPError as error:
        raise PerformanceTokenError(
            "Performance Token 网络请求失败：请检查网络、代理和服务地址。",
            code="performance_network_error",
        ) from error
    if response.status_code >= 400:
        raise _token_http_error(response)
    try:
        body: Any = response.json()
    except ValueError as error:
        raise PerformanceTokenError(
            f"Performance Token 响应格式无效（HTTP {response.status_code}，"
            f"Content-Type {_content_type(response)}）；请检查接口地址、网络代理和服务状态。",
            code="performance_upstream_invalid_response",
        ) from error
    access_token = body.get("access_token") if isinstance(body, dict) else None
    expires_in = body.get("expires_in") if isinstance(body, dict) else None
    if not isinstance(access_token, str) or not access_token.strip():
        raise PerformanceTokenError(
            "Performance Token 响应缺少 access_token。请确认 Performance 凭据和授权范围。",
            code="performance_upstream_invalid_response",
        )
    if not isinstance(expires_in, (int, float)) or expires_in <= 0:
        raise PerformanceTokenError(
            "Performance Token 响应缺少有效 expires_in。请确认 Performance 接口返回格式。",
            code="performance_upstream_invalid_response",
        )
    return access_token, datetime.now(UTC) + timedelta(seconds=float(expires_in))


class PerformanceApiError(RuntimeError):
    """Performance API 只读请求失败；异常信息不得包含令牌或密钥。"""

    def __init__(self, message: str, *, code: str = "performance_api_failed") -> None:
        """初始化对象依赖和运行时状态。"""
        super().__init__(message)
        self.code = code


async def fetch_performance_campaigns(
    *, access_token: str, timeout_seconds: float = 20.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """读取广告活动列表，不执行任何写操作。"""
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, transport=transport) as client:
            response = await client.get(
                PERFORMANCE_CAMPAIGNS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as error:
        raise PerformanceApiError("Performance 广告活动查询请求失败") from error
    if response.status_code >= 400:
        code = {
            401: "performance_oauth_failed",
            403: "performance_permission_denied",
        }.get(response.status_code, "performance_api_failed")
        raise PerformanceApiError(
            f"Performance 广告活动查询失败（HTTP {response.status_code}）", code=code
        )
    try:
        body: Any = response.json()
    except ValueError as error:
        raise PerformanceApiError("Performance 广告活动响应不是合法 JSON") from error
    if not isinstance(body, dict):
        raise PerformanceApiError("Performance 广告活动响应格式无效")
    return body
