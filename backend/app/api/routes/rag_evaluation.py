"""评测案例 API：AI 只生成草稿，确认必须由人工完成。"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.rag_evaluation import EvaluationCase, confirm_case, suite_case_limit
from backend.app.domain.rag_evaluation_corpus import fixed_evaluation_corpus, fixed_suite_case_ids
from backend.app.domain.rag_metrics import (
    EvaluationObservation,
    calculate_metrics,
    quality_gate_passed,
)

router = APIRouter(prefix="/v1/rag-evaluation", tags=["rag-evaluation"])
_cases: dict[str, EvaluationCase] = {}
for _fixed in fixed_evaluation_corpus():
    _cases[_fixed.case_id] = EvaluationCase(
        case_id=_fixed.case_id, question=_fixed.question,
        expected_status=_fixed.expected_status, expected_sources=_fixed.expected_chunk_ids,
        safety_tags=_fixed.safety_tags,
    )


class CaseGenerationPayload(BaseModel):
    topics: list[str] = Field(min_length=1, max_length=20)


class EvaluationCaseResponse(BaseModel):
    case_id: str
    question: str
    expected_status: str
    expected_sources: list[str]
    safety_tags: list[str]
    status: str


class ConfirmPayload(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)


class EvaluationRunPayload(BaseModel):
    suite: str = Field(pattern="^(quick|standard|full)$")


class MetricObservationPayload(BaseModel):
    expected_chunk_ids: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    cited_chunk_ids: list[str] = Field(default_factory=list)
    expected_status: str
    actual_status: str
    latency_ms: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    ranked_retrieved_chunk_ids: list[str] = Field(default_factory=list)
    multi_intent_complete: bool = True
    safety_passed: bool = True
    degradation_expected: bool = False
    degradation_observed: bool = False


def _response(case: EvaluationCase) -> EvaluationCaseResponse:
    return EvaluationCaseResponse(
        case_id=case.case_id, question=case.question, expected_status=case.expected_status,
        expected_sources=list(case.expected_sources), safety_tags=list(case.safety_tags),
        status=case.status,
    )


@router.post("/case-generation-jobs", response_model=list[EvaluationCaseResponse], status_code=201)
async def generate_evaluation_cases(payload: CaseGenerationPayload) -> list[EvaluationCaseResponse]:
    generated: list[EvaluationCaseResponse] = []
    for topic in payload.topics:
        case = EvaluationCase(
            case_id=str(uuid4()), question=f"请说明{topic}的处理规则", expected_status="answered",
            expected_sources=(), safety_tags=("generated_draft",),
        )
        _cases[case.case_id] = case
        generated.append(_response(case))
    return generated


@router.get("/cases", response_model=list[EvaluationCaseResponse])
async def list_evaluation_cases() -> list[EvaluationCaseResponse]:
    return [_response(case) for case in _cases.values()]


@router.post("/cases/{case_id}/confirm", response_model=EvaluationCaseResponse)
async def confirm_evaluation_case(case_id: str, payload: ConfirmPayload) -> EvaluationCaseResponse:
    case = _cases.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="评测案例不存在")
    confirmed = confirm_case(case, reviewer=payload.reviewer)
    _cases[case_id] = confirmed
    return _response(confirmed)


@router.post("/runs", response_model=dict[str, object], status_code=202)
async def start_evaluation(payload: EvaluationRunPayload) -> dict[str, object]:
    limit = suite_case_limit(payload.suite)
    target_ids = fixed_suite_case_ids(payload.suite)
    confirmed = [case_id for case_id in target_ids if _cases[case_id].status == "confirmed"]
    return {
        "run_id": str(uuid4()), "status": "queued", "suite": payload.suite,
        "target_count": limit, "confirmed_count": len(confirmed),
        "case_ids": list(target_ids),
        "gate_status": "ready" if len(confirmed) == limit else "blocked",
    }


@router.post("/metrics", response_model=dict[str, object])
async def calculate_evaluation_metrics(
    observations: list[MetricObservationPayload],
) -> dict[str, object]:
    metrics = calculate_metrics([
        EvaluationObservation(
            expected_chunk_ids=frozenset(item.expected_chunk_ids),
            retrieved_chunk_ids=frozenset(item.retrieved_chunk_ids),
            cited_chunk_ids=frozenset(item.cited_chunk_ids),
            expected_status=item.expected_status, actual_status=item.actual_status,
            latency_ms=item.latency_ms, estimated_cost=item.estimated_cost,
            ranked_retrieved_chunk_ids=tuple(item.ranked_retrieved_chunk_ids),
            multi_intent_complete=item.multi_intent_complete,
            safety_passed=item.safety_passed,
            degradation_expected=item.degradation_expected,
            degradation_observed=item.degradation_observed,
        )
        for item in observations
    ])
    return {
        "recall": metrics.recall, "precision": metrics.precision,
        "citation_support_rate": metrics.citation_support_rate,
        "correct_refusal_rate": metrics.correct_refusal_rate,
        "average_latency_ms": metrics.average_latency_ms,
        "estimated_cost": metrics.estimated_cost,
        "recall_at_5": metrics.recall_at_5,
        "recall_at_10": metrics.recall_at_10,
        "precision_at_5": metrics.precision_at_5,
        "multi_intent_completeness": metrics.multi_intent_completeness,
        "safety_pass_rate": metrics.safety_pass_rate,
        "degradation_pass_rate": metrics.degradation_pass_rate,
        "gate_status": "passed" if quality_gate_passed(metrics) else "blocked",
    }
