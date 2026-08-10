from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_store_workspace_gateway
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import create_app


class StubWorkspaceGateway:
    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        if workspace_id != "store-1":
            return None
        now = datetime.now(UTC)
        return StoreWorkspace(
            id=workspace_id,
            display_name="测试店铺",
            status="active",
            verified_at=now,
            created_at=now,
            updated_at=now,
        )


def test_keyword_csv_preview_is_workspace_scoped() -> None:
    app = create_app()
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway
    response = TestClient(app).post(
        "/v1/store-workspaces/store-1/keyword-report-imports/preview",
        content="keyword,search_count,conversion_rate\nкружка,10,2%\n",
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["rows"][0]["keyword"] == "кружка"
    assert len(response.json()["fingerprint"]) == 64


def test_mapped_keyword_csv_preview_returns_internal_fields() -> None:
    app = create_app()
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway
    response = TestClient(app).post(
        "/v1/store-workspaces/store-1/keyword-report-imports/preview-mapped",
        json={
            "content": "term,volume,rate\nкружка,10,2%\n",
            "column_mapping": {
                "term": "keyword",
                "volume": "search_count",
                "rate": "conversion_rate",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["rows"][0]["search_count"] == 10
    assert len(response.json()["fingerprint"]) == 64
