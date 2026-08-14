from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_default_organization_id,
    get_identity_service,
    get_login_rate_limiter,
    get_session_cookie_secure,
)
from backend.app.domain.identity import AuthenticatedUser, LoginResult
from backend.app.main import create_app


@dataclass(slots=True)
class FakeIdentityService:
    result: LoginResult | None
    revoked: list[str] = field(default_factory=list)

    async def login(self, email: str, password: str, organization_id: str) -> LoginResult | None:
        del email, password, organization_id
        return self.result

    async def authenticate(self, token: str) -> AuthenticatedUser | None:
        if self.result is not None and token == self.result.token:
            return self.result.user
        return None

    async def logout(self, token: str) -> None:
        self.revoked.append(token)


@dataclass(slots=True)
class FakeLimiter:
    retry_seconds: int | None = None
    failures: int = 0
    clears: int = 0

    async def retry_after(self, email: str, client_key: str) -> int | None:
        del email, client_key
        return self.retry_seconds

    async def record_failure(self, email: str, client_key: str) -> None:
        del email, client_key
        self.failures += 1

    async def clear(self, email: str, client_key: str) -> None:
        del email, client_key
        self.clears += 1


def _client(service: FakeIdentityService, limiter: FakeLimiter) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_identity_service] = lambda: service
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_session_cookie_secure] = lambda: False
    app.dependency_overrides[get_default_organization_id] = lambda: "org-1"
    return TestClient(app)


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id="user-1",
        email="owner@example.com",
        display_name="Owner",
        organization_id="org-1",
        organization_role="owner",
    )


def test_login_sets_http_only_cookie_and_me_uses_session() -> None:
    result = LoginResult(
        token="raw-session-token",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=_user(),
    )
    limiter = FakeLimiter()
    client = _client(FakeIdentityService(result), limiter)

    login = client.post(
        "/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "long-test-password",
        },
    )
    me = client.get("/v1/auth/me")

    assert login.status_code == 200
    assert login.headers["cache-control"] == "no-store"
    assert "HttpOnly" in login.headers["set-cookie"]
    assert me.status_code == 200
    assert me.headers["cache-control"] == "no-store"
    assert me.json()["role"] == "owner"


def test_logout_returns_no_content_and_revokes_session() -> None:
    result = LoginResult(
        token="logout-session-token",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=_user(),
    )
    service = FakeIdentityService(result)
    client = _client(service, FakeLimiter())

    login = client.post(
        "/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-password"},
    )
    response = client.post("/v1/auth/logout")

    assert login.status_code == 200
    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert service.revoked == ["logout-session-token"]


def test_invalid_login_records_failure_and_rate_limit_returns_retry_after() -> None:
    limiter = FakeLimiter()
    client = _client(FakeIdentityService(None), limiter)
    payload = {
        "email": "owner@example.com",
        "password": "wrong-password-value",
    }

    invalid = client.post("/v1/auth/login", json=payload)
    limiter.retry_seconds = 30
    limited = client.post("/v1/auth/login", json=payload)

    assert invalid.status_code == 401
    assert limiter.failures == 1
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "30"
