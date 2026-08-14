from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_quality_check_endpoint_returns_findings() -> None:
    response = TestClient(create_app()).post(
        "/v1/data-quality/check",
        json={
            "record": {"status": "unknown"},
            "required_fields": ["offer_id"],
            "enum_fields": {"status": ["active"]},
        },
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert {item["rule_code"] for item in response.json()["findings"]} == {
        "DQ-003-MISSING",
        "DQ-003-ENUM",
    }
