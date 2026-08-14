from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_knowledge_query_plan_returns_multi_intent_status() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/knowledge-answers/plan",
            json={"question": "字段是什么意思？删除这个版本"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "planned"
    assert len(body["segments"]) == 2
    assert body["segments"][1]["intent"] == "restricted_action"
    assert "尚未接入" in body["message"]
