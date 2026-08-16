from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_default_organization_id,
    get_identity_service,
    get_login_rate_limiter,
    get_session_cookie_secure,
)
from backend.app.domain.identity import AuthenticatedUser, LoginResult
from backend.app.main import app


class _IdentityService:
    async def login(self, email: str, password: str) -> LoginResult | None:
        if email != "admin@example.com" or password != "correct-password":
            return None
        return LoginResult(
            token="raw-session-token",
            expires_at=datetime(2026, 8, 4, tzinfo=UTC),
            user=AuthenticatedUser(
                id="operator-admin",
                email=email,
                display_name="Admin",
                role="admin",
                workspace_ids=("workspace-1",),
            ),
        )

    async def authenticate(self, token: str) -> AuthenticatedUser | None:
        if token != "raw-session-token":
            return None
        return AuthenticatedUser(
            id="operator-admin",
            email="admin@example.com",
            display_name="Admin",
            role="admin",
            workspace_ids=("workspace-1",),
        )

    async def logout(self, token: str) -> None:
        assert token == "raw-session-token"


class _BlockedLoginLimiter:
    async def retry_after(self, email: str, client_key: str) -> int | None:
        assert email == "admin@example.com"
        assert client_key == "testclient"
        return 42

    async def record_failure(self, email: str, client_key: str) -> None:
        raise AssertionError("blocked attempt must not be recorded again")

    async def clear(self, email: str, client_key: str) -> None:
        raise AssertionError("blocked attempt cannot clear the limiter")


class _LoginLimiter:
    async def retry_after(self, email: str, client_key: str) -> int | None:
        return None

    async def record_failure(self, email: str, client_key: str) -> None:
        return None

    async def clear(self, email: str, client_key: str) -> None:
        return None


@pytest.fixture(autouse=True)
def _rate_limiter_override() -> None:
    app.dependency_overrides[get_login_rate_limiter] = _LoginLimiter
    # 认证单测只验证会话行为；固定测试租户和 Cookie 策略，避免读取本地部署配置。
    app.dependency_overrides[get_default_organization_id] = lambda: "test-organization"
    app.dependency_overrides[get_session_cookie_secure] = lambda: False
    yield
    app.dependency_overrides.clear()


def test_login_sets_http_only_cookie_and_returns_user() -> None:
    app.dependency_overrides[get_identity_service] = _IdentityService
    try:
        response = TestClient(app).post(
            "/v1/auth/login",
            json={"email": "ADMIN@example.com", "password": "correct-password"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["display_name"] == "Admin"
    assert response.json()["session_token"] == "raw-session-token"
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "raw-session-token" in cookie


def test_login_rejects_invalid_credentials_without_setting_cookie() -> None:
    app.dependency_overrides[get_identity_service] = _IdentityService
    try:
        response = TestClient(app).post(
            "/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong-password"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_login_rate_limit_returns_retry_after() -> None:
    app.dependency_overrides[get_identity_service] = _IdentityService
    app.dependency_overrides[get_login_rate_limiter] = _BlockedLoginLimiter
    try:
        response = TestClient(app).post(
            "/v1/auth/login",
            json={"email": "admin@example.com", "password": "correct-password"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"
    assert response.json()["detail"]["message"] == "登录尝试过多，请稍后重试"


def test_https_login_does_not_expose_session_token() -> None:
    app.dependency_overrides[get_identity_service] = _IdentityService
    app.dependency_overrides[get_session_cookie_secure] = lambda: True
    try:
        response = TestClient(app).post(
            "/v1/auth/login",
            json={"email": "admin@example.com", "password": "correct-password"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "session_token" not in response.json()
    assert "secure" in response.headers["set-cookie"].lower()


def test_me_requires_a_valid_session() -> None:
    app.dependency_overrides[get_identity_service] = _IdentityService
    try:
        client = TestClient(app)
        unauthenticated = client.get("/v1/auth/me")
        client.cookies.set("ozonslj_session", "raw-session-token")
        authenticated = client.get("/v1/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200
    assert authenticated.json()["email"] == "admin@example.com"


def test_logout_revokes_and_clears_session_cookie() -> None:
    app.dependency_overrides[get_identity_service] = _IdentityService
    try:
        client = TestClient(app)
        client.cookies.set("ozonslj_session", "raw-session-token")
        response = client.post("/v1/auth/logout")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert "ozonslj_session=\"\"" in response.headers["set-cookie"]


def test_me_accepts_development_bearer_session() -> None:
    app.dependency_overrides[get_identity_service] = _IdentityService
    try:
        response = TestClient(app).get(
            "/v1/auth/me", headers={"Authorization": "Bearer raw-session-token"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "operator-admin"
