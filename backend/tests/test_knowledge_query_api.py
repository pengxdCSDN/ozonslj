"""知识问答 API 的引用与拒答回归测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.knowledge_answers import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_query_returns_citation_for_published_evidence() -> None:
    response = _client().post(
        "/v1/knowledge-answers/query", json={"question": "如何使用 RAG"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["segments"][0]["citations"][0]["source_locator"] == "docs/rag/demo.md"
    trace = _client().get(f"/v1/knowledge-answers/{body['answer_id']}/trace")
    assert trace.status_code == 200
    assert len(trace.json()["question_hash"]) == 64


def test_query_refuses_write_intent() -> None:
    response = _client().post("/v1/knowledge-answers/query", json={"question": "发布这个商品"})

    assert response.status_code == 200
    body = response.json()
    assert body["segments"][0]["status"] == "refused"
    assert body["segments"][0]["citations"] == []
