from dataclasses import replace

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_current_user, get_seller_account_service
from backend.app.application.seller_accounts import SellerAccountService
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.seller_account import (
    CreatedSellerAccount,
    SellerAccountConflictError,
    SellerCredentialValidationError,
)
from backend.app.main import app


class _Protector:
    key_version = 4

    def encrypt(self, api_key: str) -> bytes:
        assert api_key == "secret-key"
        return b"encrypted-only"


class _Verifier:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.credentials: tuple[str, str] | None = None

    async def verify(self, *, client_id: str, api_key: str) -> None:
        self.credentials = (client_id, api_key)
        if self.fail:
            raise SellerCredentialValidationError("Ozon 凭据无效")


class _Gateway:
    def __init__(self, *, conflict: bool = False) -> None:
        self.conflict = conflict
        self.created: dict[str, object] | None = None

    async def create(self, **values: object) -> CreatedSellerAccount:
        if self.conflict:
            raise SellerAccountConflictError("该 Ozon Client-Id 已存在")
        self.created = values
        return CreatedSellerAccount(
            seller_account_id=str(values["seller_account_id"]),
            workspace_id=str(values["workspace_id"]),
            display_name=str(values["display_name"]),
            workspace_name=str(values["workspace_name"]),
        )


ADMIN = AuthenticatedUser(
    id="operator-admin",
    email="admin@example.com",
    display_name="Admin",
    role="admin",
    workspace_ids=(),
)


def _service(*, verifier_fail: bool = False, conflict: bool = False) -> SellerAccountService:
    return SellerAccountService(
        _Gateway(conflict=conflict),
        _Verifier(fail=verifier_fail),
        _Protector(),
    )


def _create(service: SellerAccountService, user: AuthenticatedUser = ADMIN):
    app.dependency_overrides[get_seller_account_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        return TestClient(app).post(
            "/v1/seller-accounts",
            json={
                "display_name": " Ozon 主店 ",
                "workspace_name": " 主店工作区 ",
                "client_id": " 123456 ",
                "api_key": " secret-key ",
            },
        )
    finally:
        app.dependency_overrides.clear()


def test_admin_creates_verified_encrypted_seller_account() -> None:
    gateway = _Gateway()
    verifier = _Verifier()
    service = SellerAccountService(gateway, verifier, _Protector())

    response = _create(service)

    assert response.status_code == 201
    assert response.json()["status"] == "active"
    assert verifier.credentials == ("123456", "secret-key")
    assert gateway.created is not None
    assert gateway.created["encrypted_api_key"] == b"encrypted-only"
    assert gateway.created["credential_version"] == 4
    assert "secret-key" not in response.text
    assert "client_id" not in response.text


def test_non_admin_cannot_create_seller_account() -> None:
    response = _create(_service(), replace(ADMIN, organization_role="operator"))

    assert response.status_code == 403


def test_invalid_ozon_credentials_are_not_persisted() -> None:
    gateway = _Gateway()
    service = SellerAccountService(gateway, _Verifier(fail=True), _Protector())

    response = _create(service)

    assert response.status_code == 422
    assert gateway.created is None
    assert "secret-key" not in response.text


def test_duplicate_client_id_returns_conflict_without_credentials() -> None:
    response = _create(_service(conflict=True))

    assert response.status_code == 409
    assert "secret-key" not in response.text
