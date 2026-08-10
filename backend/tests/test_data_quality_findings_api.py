from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_quality_finding_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.data_quality import QualityFinding, QualityFindingRecord
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import create_app


class StubQualityGateway:
    def __init__(self) -> None:
        self.record = QualityFindingRecord(
            id="finding-1", workspace_id="store-1", rule_code="DQ-005-STOCK",
            field_name="available_stock", severity="error", message="库存异常",
            created_at=datetime.now(UTC),
        )

    async def list_findings(
        self, *, workspace_id: str, status: str | None, limit: int
    ) -> list[QualityFindingRecord]:
        del status, limit
        return [self.record] if workspace_id == self.record.workspace_id else []

    async def create_findings(
        self, *, workspace_id: str, findings: list[QualityFinding]
    ) -> list[QualityFindingRecord]:
        del workspace_id
        return [
            self.record.model_copy(update={"rule_code": item.rule_code})
            for item in findings
        ]

    async def update_status(self, *, finding_id: str, status: str) -> QualityFindingRecord | None:
        if finding_id != self.record.id:
            return None
        self.record = self.record.model_copy(update={"status": status})
        return self.record


class StubWorkspaceGateway:
    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        if workspace_id != "store-1":
            return None
        now = datetime.now(UTC)
        return StoreWorkspace(
            id="store-1",
            display_name="测试店铺",
            status="active",
            verified_at=now,
            created_at=now,
            updated_at=now,
        )


def test_quality_findings_can_be_listed_and_resolved() -> None:
    app = create_app()
    gateway = StubQualityGateway()
    app.dependency_overrides[get_quality_finding_gateway] = lambda: gateway
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway
    client = TestClient(app)

    listed = client.get("/v1/store-workspaces/store-1/data-quality/findings?status=open")
    resolved = client.patch(
        "/v1/store-workspaces/store-1/data-quality/findings/finding-1",
        json={"status": "resolved"},
    )

    assert listed.status_code == 200
    assert listed.json()[0]["rule_code"] == "DQ-005-STOCK"
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_quality_findings_can_be_created_for_a_workspace() -> None:
    app = create_app()
    gateway = StubQualityGateway()
    app.dependency_overrides[get_quality_finding_gateway] = lambda: gateway
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway

    response = TestClient(app).post(
        "/v1/store-workspaces/store-1/data-quality/findings",
        json=[
            {
                "rule_code": "DQ-006-CONFLICT",
                "field_name": "price",
                "severity": "warning",
                "message": "冲突",
            }
        ],
    )

    assert response.status_code == 201
    assert response.json()[0]["rule_code"] == "DQ-006-CONFLICT"
