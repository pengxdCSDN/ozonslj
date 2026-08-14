from fastapi.testclient import TestClient

from backend.app.main import app


def test_quality_schema_api_returns_findings() -> None:
    response = TestClient(app).post(
        "/v1/data-quality/schema-check",
        json={
            "rows": [{"status": "bad"}],
            "required_fields": ["sku"],
            "enum_fields": {"status": ["active"]},
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["isolated_required"] is True
