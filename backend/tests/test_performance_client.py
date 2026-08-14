import json
from datetime import UTC

import httpx
import pytest

from backend.app.infrastructure.ozon.performance_client import request_performance_token


@pytest.mark.asyncio
async def test_request_performance_token_uses_client_credentials() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/client/token"
        assert request.headers["content-type"] == "application/json"
        assert json.loads(request.content) == {
            "client_id": "client-id",
            "client_secret": "client-secret",
            "grant_type": "client_credentials",
        }
        return httpx.Response(200, json={"access_token": "access", "expires_in": 3600})

    token, expires_at = await request_performance_token(
        client_id="client-id",
        client_secret="client-secret",
        transport=httpx.MockTransport(handler),
    )

    assert token == "access"
    assert expires_at.tzinfo == UTC
