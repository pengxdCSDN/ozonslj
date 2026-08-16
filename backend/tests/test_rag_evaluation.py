"""评测案例必须人工确认后才能进入评测运行。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_rag_evaluation_gateway
from backend.app.api.routes.rag_evaluation import router
from backend.app.domain.rag_evaluation import EvaluationCase
from backend.app.domain.rag_evaluation_corpus import fixed_evaluation_corpus, fixed_suite_case_ids


class MemoryEvaluationGateway:
    """路由测试替身；用同一个实例模拟 PostgreSQL 跨请求保留确认状态。"""

    def __init__(self) -> None:
        self.cases = {
            item.case_id: EvaluationCase(
                case_id=item.case_id, question=item.question, expected_status=item.expected_status,
                expected_sources=item.expected_chunk_ids, safety_tags=item.safety_tags,
            ) for item in fixed_evaluation_corpus()
        }

    async def seed_fixed_cases(self, cases: list[EvaluationCase]) -> None:
        for case in cases:
            self.cases.setdefault(case.case_id, case)

    async def create_case(self, case: EvaluationCase) -> EvaluationCase:
        self.cases[case.case_id] = case
        return case

    async def list_cases(self) -> list[EvaluationCase]:
        return list(self.cases.values())

    async def confirm_case(self, case_id: str, reviewer: str) -> EvaluationCase | None:
        case = self.cases.get(case_id)
        if case is None:
            return None
        confirmed = EvaluationCase(
            case_id=case.case_id, question=case.question, expected_status=case.expected_status,
            expected_sources=case.expected_sources, safety_tags=case.safety_tags,
            status="confirmed",
        )
        self.cases[case_id] = confirmed
        return confirmed

    async def confirm_cases(self, case_ids: list[str], reviewer: str) -> list[EvaluationCase]:
        result = []
        for case_id in dict.fromkeys(case_ids):
            case = await self.confirm_case(case_id, reviewer)
            if case is not None:
                result.append(case)
        return result

    async def create_run(self, suite: str, gate_status: str) -> str:
        return f"test-run-{suite}"


def make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    gateway = MemoryEvaluationGateway()
    app.dependency_overrides[get_rag_evaluation_gateway] = lambda: gateway
    return app


def test_generate_confirm_and_run() -> None:
    client = TestClient(make_app())
    generated = client.post(
        "/v1/rag-evaluation/case-generation-jobs", json={"topics": ["库存同步"]}
    )
    case_id = generated.json()[0]["case_id"]
    assert generated.json()[0]["status"] == "draft"
    confirmed = client.post(
        f"/v1/rag-evaluation/cases/{case_id}/confirm", json={"reviewer": "root"}
    )
    assert confirmed.json()["status"] == "confirmed"
    fixed_id = fixed_suite_case_ids("quick")[0]
    confirmed_fixed = client.post(
        f"/v1/rag-evaluation/cases/{fixed_id}/confirm", json={"reviewer": "root"}
    )
    assert confirmed_fixed.json()["status"] == "confirmed"
    run = client.post("/v1/rag-evaluation/runs", json={"suite": "quick"})
    assert run.status_code == 202
    assert run.json()["gate_status"] == "blocked"
    assert run.json()["target_count"] == 30
    assert run.json()["confirmed_count"] == 1


def test_metrics_api_returns_quality_indicators() -> None:
    response = TestClient(make_app()).post(
        "/v1/rag-evaluation/metrics",
        json=[{
            "expected_chunk_ids": ["c1"], "retrieved_chunk_ids": ["c1"],
            "cited_chunk_ids": ["c1"], "expected_status": "answered",
            "actual_status": "answered", "latency_ms": 20, "estimated_cost": 0.1,
        }],
    )
    assert response.json()["recall"] == 1
    assert response.json()["citation_support_rate"] == 1


def test_batch_confirmation_is_idempotent_and_persists_between_requests() -> None:
    client = TestClient(make_app())
    case_ids = list(fixed_suite_case_ids("quick"))[:2]
    first = client.post(
        "/v1/rag-evaluation/cases/confirm-batch",
        json={"case_ids": case_ids, "reviewer": "qa-user"},
    )
    assert first.status_code == 200
    assert first.json()["confirmed_count"] == 2
    second = client.post(
        "/v1/rag-evaluation/cases/confirm-batch",
        json={"case_ids": case_ids, "reviewer": "qa-user"},
    )
    assert second.json()["confirmed_count"] == 2
    page = client.get("/v1/rag-evaluation/cases?page=2&page_size=100").json()
    cases = {item["case_id"]: item for item in page["items"]}
    assert all(cases[case_id]["status"] == "confirmed" for case_id in case_ids)


def test_case_list_hides_retired_fixed_corpus_versions() -> None:
    app = make_app()
    gateway = next(iter(app.dependency_overrides.values()))()
    gateway.cases["fixed-rag-001"] = EvaluationCase(
        case_id="fixed-rag-001", question="旧案例", expected_status="answered",
        expected_sources=(), safety_tags=(), status="confirmed",
    )
    cases = TestClient(app).get("/v1/rag-evaluation/cases").json()["items"]
    ids = {case["case_id"] for case in cases}
    assert "fixed-rag-001" not in ids
    assert "fixed-rag-v2-001" in ids


def test_case_list_supports_search_and_pagination() -> None:
    response = TestClient(make_app()).get(
        "/v1/rag-evaluation/cases", params={"q": "Embedding", "page": 1, "page_size": 2}
    )
    body = response.json()
    assert response.status_code == 200
    assert body["total"] > 0
    assert len(body["items"]) <= 2
    assert all("Embedding" in item["question"] for item in body["items"])
