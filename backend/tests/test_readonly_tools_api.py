from fastapi.testclient import TestClient

from backend.app.main import app


def test_readonly_tool_api_rejects_sql() -> None:
    response = TestClient(app).post(
        "/v1/assistant/tools/authorize",
        json={"tool": "sales_summary", "parameters": {"sql": "SELECT 1"}},
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is False
    assert response.json()["sql_allowed"] is False
