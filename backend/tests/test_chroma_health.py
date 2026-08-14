"""Chroma 健康探针不泄露正文且能区分服务状态。"""

import httpx
import pytest

from backend.app.infrastructure.local.chroma_health import ChromaHealthProbe


@pytest.mark.asyncio
async def test_chroma_health_probe_reports_healthy_without_reading_body() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/heartbeat"
        return httpx.Response(200, json={"nanoseconds": 1})

    probe = ChromaHealthProbe(
        "http://chroma:8000", transport=httpx.MockTransport(handler)
    )
    result = await probe.check()
    assert result.state == "healthy"
    assert result.detail is None


@pytest.mark.asyncio
async def test_chroma_health_probe_handles_unconfigured_and_timeout() -> None:
    unconfigured = await ChromaHealthProbe(None).check()
    assert unconfigured.state == "not_configured"

    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    timeout = await ChromaHealthProbe(
        "http://chroma:8000", transport=httpx.MockTransport(timeout_handler)
    ).check()
    assert timeout.state == "unhealthy"
