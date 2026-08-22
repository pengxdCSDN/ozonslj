"""受控公开页面 HTTP 适配器；不绕过 robots、域名白名单或限流策略。"""

from collections.abc import Collection
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from backend.app.domain.public_sampling import FetchResponse


class PublicHttpFetcher:
    """读取白名单 HTTPS 页面；页面请求前先读取并校验 robots.txt。"""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        allowed_hosts: Collection[str],
        user_agent: str = "ozonslj-public-sampler/1.0",
    ) -> None:
        self._client = client
        self._allowed_hosts = frozenset(host.lower() for host in allowed_hosts)
        self._user_agent = user_agent

    async def fetch_page(self, url: str) -> FetchResponse | tuple[int, float | None]:
        """在合规检查通过后读取页面状态；不返回页面正文，避免原始 HTML 落库。"""
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not hostname:
            return FetchResponse(None, False, "仅允许白名单 HTTPS 页面")
        if hostname not in self._allowed_hosts:
            return FetchResponse(None, False, "页面域名不在公开采样白名单")

        robots = await self._client.get(f"https://{hostname}/robots.txt")
        if robots.status_code in {401, 403}:
            return FetchResponse(robots.status_code, False, "robots 策略禁止访问")
        if robots.status_code not in {200, 404}:
            return _retry_response(robots)
        if robots.status_code == 200:
            parser = RobotFileParser()
            parser.set_url(f"https://{hostname}/robots.txt")
            parser.parse(robots.text.splitlines())
            if not parser.can_fetch(self._user_agent, url):
                return FetchResponse(robots.status_code, False, "robots 策略禁止访问")

        response = await self._client.get(url, headers={"User-Agent": self._user_agent})
        result = _retry_response(response)
        if isinstance(result, FetchResponse) and result.allowed:
            return result.__class__(
                result.status_code, result.allowed, result.message, response.text
            )
        return result


def _retry_response(response: httpx.Response) -> FetchResponse | tuple[int, float | None]:
    """将 HTTP 状态转换为采样器可处理的有限退避结果。"""
    if response.status_code not in {429, 503}:
        return FetchResponse(response.status_code, True, "请求完成")
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return response.status_code, None
    try:
        return response.status_code, max(0.0, float(retry_after))
    except ValueError:
        # 日期格式的 Retry-After 需要服务端时钟，无法可靠地从 Mock/异步客户端推断；
        # 返回 None 让领域层使用其安全的零等待退避边界，不把异常头当作无限等待。
        return response.status_code, None
