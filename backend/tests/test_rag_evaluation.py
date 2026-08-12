"""评测案例必须人工确认后才能进入评测运行。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.rag_evaluation import router


def test_generate_confirm_and_run() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    generated = client.post(
        "/v1/rag-evaluation/case-generation-jobs", json={"topics": ["库存同步"]}
    )
    case_id = generated.json()[0]["case_id"]
    assert generated.json()[0]["status"] == "draft"
    confirmed = client.post(
        f"/v1/rag-evaluation/cases/{case_id}/confirm", json={"reviewer": "root"}
    )
    assert confirmed.json()["status"] == "confirmed"
    run = client.post("/v1/rag-evaluation/runs", json={"suite": "quick"})
    assert run.status_code == 202
    assert run.json()["gate_status"] == "ready"


def test_metrics_api_returns_quality_indicators() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/v1/rag-evaluation/metrics",
        json=[{
            "expected_chunk_ids": ["c1"], "retrieved_chunk_ids": ["c1"],
            "cited_chunk_ids": ["c1"], "expected_status": "answered",
            "actual_status": "answered", "latency_ms": 20, "estimated_cost": 0.1,
        }],
    )
    assert response.json()["recall"] == 1
    assert response.json()["citation_support_rate"] == 1
