"""RAG 能力探针和试运行切换测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.rag_rollout import router


def test_capability_and_rollout_transition() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    capability = client.get("/v1/capabilities/knowledge-rag")
    assert capability.json()["knowledge_query"] is True
    changed = client.post(
        "/v1/rag-rollout/transitions", json={"mode": "shadow", "reason": "先观察"}
    )
    assert changed.json()["mode"] == "shadow"
