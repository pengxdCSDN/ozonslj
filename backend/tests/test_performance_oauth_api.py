from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.api.routes import performance_oauth
from backend.app.domain.performance_credentials import PerformanceCredentialStatus
from backend.app.main import create_app


def test_performance_oauth_api_does_not_echo_refresh_token() -> None:
    response = TestClient(create_app()).post(
        "/v1/advertising/performance-oauth/inspect",
        json={
            "access_token": "perf-token",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "refresh_token": "secret-refresh",
        },
    )
    assert response.status_code == 200
    assert "secret-refresh" not in response.text
    assert response.json()["credential_scope"] == "performance_api"


class _PerformanceCredentialGateway:
    """为自动换 Token 回归测试提供不接触 PostgreSQL 的最小凭据端口。"""

    def __init__(self, expires_at: str) -> None:
        self.expires_at = expires_at
        self.saved_tokens: list[tuple[str, str]] = []

    async def get_access_token(self, *, workspace_id: str) -> tuple[str, str] | None:
        del workspace_id
        return "expired-token", self.expires_at

    async def get_client_credentials(self, *, workspace_id: str) -> tuple[str, str]:
        del workspace_id
        return "client-id", "client-secret"

    async def save_client_credentials(
        self, *, workspace_id: str, client_id: str, client_secret: str
    ) -> PerformanceCredentialStatus:
        del workspace_id, client_id, client_secret
        raise AssertionError("测试不应重新保存 Client 凭据")

    async def get_status(self, *, workspace_id: str) -> PerformanceCredentialStatus | None:
        del workspace_id
        return None

    async def save_tokens(
        self, *, workspace_id: str, access_token: str, refresh_token: str | None,
        expires_at: str, client_id_present: bool,
    ) -> PerformanceCredentialStatus:
        del workspace_id, refresh_token, client_id_present
        self.saved_tokens.append((access_token, expires_at))
        return PerformanceCredentialStatus(
            credential_scope="performance_api", client_id_present=True,
            client_secret_present=True, access_token_present=True,
            refresh_token_present=False, expires_at=expires_at,
            isolated_from_seller=True, ready=True,
        )


@pytest.mark.asyncio
async def test_expired_performance_token_is_refreshed_before_read_only_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """已过期令牌必须在只读调用前自动换取，不能要求浏览器先手动点击。"""
    gateway = _PerformanceCredentialGateway("2020-01-01T00:00:00+00:00")

    async def fake_request_token(
        *, client_id: str, client_secret: str
    ) -> tuple[str, datetime]:
        assert (client_id, client_secret) == ("client-id", "client-secret")
        return "new-token", datetime.now(UTC)

    monkeypatch.setattr(performance_oauth, "request_performance_token", fake_request_token)
    token = await performance_oauth._ensure_performance_access_token("workspace-1", gateway)

    assert token == "new-token"
    assert len(gateway.saved_tokens) == 1
    assert gateway.saved_tokens[0][0] == "new-token"
