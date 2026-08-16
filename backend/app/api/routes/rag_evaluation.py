"""评测案例 API：AI 只生成草稿，确认必须由人工完成。"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_rag_evaluation_gateway
from backend.app.domain.rag_evaluation import EvaluationCase, RagEvaluationGateway, suite_case_limit
from backend.app.domain.rag_evaluation_corpus import fixed_evaluation_corpus, fixed_suite_case_ids
from backend.app.domain.rag_metrics import (
    EvaluationObservation,
    calculate_metrics,
    quality_gate_passed,
)

router = APIRouter(prefix="/v1/rag-evaluation", tags=["rag-evaluation"])


def _fixed_cases() -> list[EvaluationCase]:
    """构造稳定的固定语料；网关负责幂等写入当前组织。"""
    return [EvaluationCase(
        case_id=item.case_id, question=item.question, expected_status=item.expected_status,
        expected_sources=item.expected_chunk_ids, safety_tags=item.safety_tags,
    ) for item in fixed_evaluation_corpus()]


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


class BatchConfirmPayload(ConfirmPayload):
    case_ids: list[str] = Field(min_length=1, max_length=240)


class BatchConfirmResponse(BaseModel):
    confirmed_count: int
    confirmed_case_ids: list[str]


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
async def generate_evaluation_cases(
    payload: CaseGenerationPayload,
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
) -> list[EvaluationCaseResponse]:
    generated: list[EvaluationCaseResponse] = []
    for topic in payload.topics:
        case = EvaluationCase(
            case_id=str(uuid4()), question=f"请说明{topic}的处理规则", expected_status="answered",
            expected_sources=(), safety_tags=("generated_draft",),
        )
        generated.append(_response(await gateway.create_case(case)))
    return generated


@router.get("/cases", response_model=list[EvaluationCaseResponse])
async def list_evaluation_cases(
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
) -> list[EvaluationCaseResponse]:
    await gateway.seed_fixed_cases(_fixed_cases())
    return [_response(case) for case in await gateway.list_cases()]


@router.post("/cases/confirm-batch", response_model=BatchConfirmResponse)
async def confirm_evaluation_cases_batch(
    payload: BatchConfirmPayload,
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
) -> BatchConfirmResponse:
    """批量确认固定语料；未知或已拒绝案例不会被伪报为已确认。"""
    confirmed = await gateway.confirm_cases(payload.case_ids, reviewer=payload.reviewer)
    return BatchConfirmResponse(
        confirmed_count=len(confirmed), confirmed_case_ids=[case.case_id for case in confirmed]
    )


@router.post("/cases/{case_id}/confirm", response_model=EvaluationCaseResponse)
async def confirm_evaluation_case(
    case_id: str,
    payload: ConfirmPayload,
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
) -> EvaluationCaseResponse:
    case = await gateway.confirm_case(case_id, reviewer=payload.reviewer)
    if case is None:
        raise HTTPException(status_code=404, detail="评测案例不存在")
    return _response(case)


@router.post("/runs", response_model=dict[str, object], status_code=202)
async def start_evaluation(
    payload: EvaluationRunPayload,
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
) -> dict[str, object]:
    await gateway.seed_fixed_cases(_fixed_cases())
    limit = suite_case_limit(payload.suite)
    target_ids = fixed_suite_case_ids(payload.suite)
    cases = {case.case_id: case for case in await gateway.list_cases()}
    confirmed = [case_id for case_id in target_ids
                 if cases.get(case_id) is not None and cases[case_id].status == "confirmed"]
    gate_status: Literal["ready", "blocked"] = (
        "ready" if len(confirmed) == limit else "blocked"
    )
    return {
        "run_id": await gateway.create_run(payload.suite, gate_status),
        "status": "queued", "suite": payload.suite,
        "target_count": limit, "confirmed_count": len(confirmed),
        "case_ids": list(target_ids),
        "gate_status": gate_status,
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
