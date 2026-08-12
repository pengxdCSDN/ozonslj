"""Chroma 向量服务健康探针。

探针只请求 Chroma heartbeat，不读取 Collection 内容，也不记录响应正文；
这样可以在 API readiness 中区分“未配置”“服务健康”和“服务不可用”，
并避免把文档正文或配置细节写入日志。
"""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

import httpx


@dataclass(frozen=True, slots=True)
class ChromaHealthStatus:
    state: str
    latency_ms: int | None
    detail: str | None


class ChromaHealthProbe:
    """通过 heartbeat 判断 Chroma 是否可被 RAG Worker 使用。"""

    def __init__(
        self,
        base_url: str | None,
        *,
        timeout_seconds: float = 2.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") if base_url else None
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def check(self) -> ChromaHealthStatus:
        if not self._base_url:
            return ChromaHealthStatus("not_configured", None, "CHROMA_URL 未配置")
        started = monotonic()
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.get("/api/v1/heartbeat")
            latency_ms = round((monotonic() - started) * 1000)
            if response.is_success:
                return ChromaHealthStatus("healthy", latency_ms, None)
            return ChromaHealthStatus("unhealthy", latency_ms, f"HTTP {response.status_code}")
        except httpx.TimeoutException:
            return ChromaHealthStatus("unhealthy", None, "heartbeat 超时")
        except httpx.NetworkError:
            return ChromaHealthStatus("unhealthy", None, "无法连接 Chroma")
