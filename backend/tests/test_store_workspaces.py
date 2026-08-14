from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_store_workspace_gateway, require_account_manager
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.store_workspace import (
    CredentialProtectionError,
    OzonAuthenticationError,
    OzonCredentials,
    StoreWorkspace,
    StoreWorkspaceStatus,
)
from backend.app.main import create_app

_API_KEY = "test-api-key-never-return"


@dataclass(slots=True)
class FakeCredentialProtector:
    namespace: bytes = b"test:"

    @property
    def key_version(self) -> int:
        return 1

    def protect(self, plaintext: str) -> bytes:
        return self.namespace + plaintext.encode()

    def unprotect(self, ciphertext: bytes, *, credential_version: int) -> str:
        if credential_version != self.key_version:
            raise CredentialProtectionError("凭据版本不可用")
        if not ciphertext.startswith(self.namespace):
            raise CredentialProtectionError("密文不可用")
        return ciphertext.removeprefix(self.namespace).decode()


@dataclass(slots=True)
class RecordingVerifier:
    error: Exception | None = None
    received: list[OzonCredentials] = field(default_factory=list)

    async def verify(self, credentials: OzonCredentials) -> None:
        self.received.append(credentials)
        if self.error is not None:
            raise self.error


class MemoryWorkspaceGateway:
    """API 用例测试替身；SQL、事务和 RLS 由 PostgreSQL 专项测试验证。"""

    def __init__(self) -> None:
        self._workspaces: dict[str, StoreWorkspace] = {}
        self._credentials: dict[str, tuple[str, bytes, int]] = {}

    async def list_workspaces(self) -> list[StoreWorkspace]:
        return list(self._workspaces.values())

    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        return self._workspaces.get(workspace_id)

    async def create_workspace(
        self,
        *,
        display_name: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> StoreWorkspace:
        now = datetime.now(UTC)
        workspace_id = f"workspace-{len(self._workspaces) + 1}"
        workspace = StoreWorkspace(
            id=workspace_id,
            display_name=display_name,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        self._workspaces[workspace_id] = workspace
        self._credentials[workspace_id] = (
            client_id,
            encrypted_api_key,
            credential_version,
        )
        return workspace

    async def replace_credentials(
        self,
        *,
        workspace_id: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> StoreWorkspace | None:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            return None
        self._credentials[workspace_id] = (
            client_id,
            encrypted_api_key,
            credential_version,
        )
        updated = workspace.model_copy(
            update={"status": "pending", "verified_at": None, "updated_at": datetime.now(UTC)}
        )
        self._workspaces[workspace_id] = updated
        return updated

    async def load_credentials(self, workspace_id: str) -> tuple[str, bytes, int] | None:
        return self._credentials.get(workspace_id)

    async def set_verification_status(
        self,
        *,
        workspace_id: str,
        status: StoreWorkspaceStatus,
        verified_at: datetime | None,
        audit_result: str,
        audit_detail: dict[str, str] | None = None,
    ) -> StoreWorkspace | None:
        del audit_result, audit_detail
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            return None
        updated = workspace.model_copy(
            update={"status": status, "verified_at": verified_at, "updated_at": datetime.now(UTC)}
        )
        self._workspaces[workspace_id] = updated
        return updated


def _client(
    gateway: MemoryWorkspaceGateway,
    *,
    verifier: RecordingVerifier | None = None,
) -> TestClient:
    app = create_app(
        credential_protector=FakeCredentialProtector(),
        seller_account_verifier=verifier or RecordingVerifier(),
    )
    app.dependency_overrides[get_store_workspace_gateway] = lambda: gateway
    app.dependency_overrides[require_account_manager] = lambda: AuthenticatedUser(
        id="owner-1",
        email="owner@example.com",
        display_name="Owner",
        organization_id="org-1",
        organization_role="owner",
    )
    return TestClient(app)


def test_create_and_verify_workspace_without_secret_leakage() -> None:
    gateway = MemoryWorkspaceGateway()
    verifier = RecordingVerifier()
    client = _client(gateway, verifier=verifier)

    created = client.post(
        "/v1/store-workspaces",
        json={"display_name": "俄罗斯主店", "client_id": "client-1", "api_key": _API_KEY},
    )
    verified = client.post(f"/v1/store-workspaces/{created.json()['id']}/verify")

    assert created.status_code == 201
    assert verified.status_code == 200
    assert verified.json()["status"] == "active"
    assert verifier.received == [OzonCredentials(client_id="client-1", api_key=_API_KEY)]
    assert _API_KEY not in created.text + verified.text


def test_authentication_failure_marks_workspace_invalid() -> None:
    gateway = MemoryWorkspaceGateway()
    client = _client(gateway, verifier=RecordingVerifier(error=OzonAuthenticationError()))
    created = client.post(
        "/v1/store-workspaces",
        json={"display_name": "俄罗斯主店", "client_id": "client-1", "api_key": _API_KEY},
    )

    response = client.post(f"/v1/store-workspaces/{created.json()['id']}/verify")

    assert response.status_code == 401
    assert (client.get("/v1/store-workspaces").json()[0]["status"]) == "invalid"
    assert _API_KEY not in response.text
