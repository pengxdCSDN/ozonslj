from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.main import create_app
from backend.tests.test_data_quality_findings_api import StubQualityGateway, StubWorkspaceGateway


def test_quality_summary_groups_findings() -> None:
    app = create_app()
    app.dependency_overrides[get_quality_finding_gateway] = StubQualityGateway
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway

    response = TestClient(app).get("/v1/store-workspaces/store-1/data-quality/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total": 1,
        "by_severity": {"error": 1},
        "by_status": {"open": 1},
        "by_rule": {"DQ-005-STOCK": 1},
    }
