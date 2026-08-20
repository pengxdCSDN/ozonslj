"""评测案例 API：AI 只生成草稿，确认必须由人工完成。"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_rag_evaluation_gateway
from backend.app.domain.rag_evaluation import (
    EvaluationCase,
    EvaluationRun,
    RagEvaluationGateway,
    suite_case_limit,
)
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
    """说明 CaseGenerationPayload 的职责、状态边界和对外协作关系。"""
    topics: list[str] = Field(min_length=1, max_length=20)


class EvaluationCaseResponse(BaseModel):
    """说明 EvaluationCaseResponse 的职责、状态边界和对外协作关系。"""
    case_id: str
    question: str
    expected_status: str
    expected_sources: list[str]
    safety_tags: list[str]
    status: str


class ConfirmPayload(BaseModel):
    """说明 ConfirmPayload 的职责、状态边界和对外协作关系。"""
    reviewer: str = Field(min_length=1, max_length=100)


class BatchConfirmPayload(ConfirmPayload):
    """说明 BatchConfirmPayload 的职责、状态边界和对外协作关系。"""
    case_ids: list[str] = Field(min_length=1, max_length=240)


class BatchConfirmResponse(BaseModel):
    """说明 BatchConfirmResponse 的职责、状态边界和对外协作关系。"""
    confirmed_count: int
    confirmed_case_ids: list[str]


class EvaluationCasesPageResponse(BaseModel):
    """说明 EvaluationCasesPageResponse 的职责、状态边界和对外协作关系。"""
    items: list[EvaluationCaseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    draft_count: int
    confirmed_count: int


class EvaluationRunPayload(BaseModel):
    """说明 EvaluationRunPayload 的职责、状态边界和对外协作关系。"""
    suite: str = Field(pattern="^(quick|standard|full)$")


class MetricObservationPayload(BaseModel):
    """说明 MetricObservationPayload 的职责、状态边界和对外协作关系。"""
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


class EvaluationRunResponse(BaseModel):
    """说明 EvaluationRunResponse 的职责、状态边界和对外协作关系。"""
    run_id: str
    suite: str
    status: str
    gate_status: str
    target_count: int
    executed_count: int
    passed_count: int
    failed_count: int
    error_count: int
    metrics: dict[str, float | str] | None = None
    error_code: str | None = None


def _run_response(run: EvaluationRun) -> EvaluationRunResponse:
    """执行内部步骤 _run_response，供同一模块的公开流程复用。"""
    return EvaluationRunResponse(
        run_id=run.run_id, suite=run.suite, status=run.status, gate_status=run.gate_status,
        target_count=run.target_count, executed_count=run.executed_count,
        passed_count=run.passed_count, failed_count=run.failed_count,
        error_count=run.error_count, metrics=run.metrics, error_code=run.error_code,
    )


def _response(case: EvaluationCase) -> EvaluationCaseResponse:
    """执行内部步骤 _response，供同一模块的公开流程复用。"""
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
    """执行 generate_evaluation_cases 的业务流程并返回该流程的结果。"""
    generated: list[EvaluationCaseResponse] = []
    for topic in payload.topics:
        case = EvaluationCase(
            case_id=str(uuid4()), question=f"请说明{topic}的处理规则", expected_status="answered",
            expected_sources=(), safety_tags=("generated_draft",),
        )
        generated.append(_response(await gateway.create_case(case)))
    return generated


@router.get("/cases", response_model=EvaluationCasesPageResponse)
async def list_evaluation_cases(
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str = Query(default="", max_length=100),
) -> EvaluationCasesPageResponse:
    """执行 list_evaluation_cases 的业务流程并返回该流程的结果。"""
    await gateway.seed_fixed_cases(_fixed_cases())
    current_fixed_ids = {case.case_id for case in _fixed_cases()}
    # v2 固定语料替换 v1 后，历史案例仍需保留在 PostgreSQL 以便审计，
    # 但页面和评测门禁只能展示当前版本；否则用户会看到 800 条重复案例，
    # 误以为新评测集未加载。AI 生成的 UUID 案例不受此过滤影响。
    visible = [
        case for case in await gateway.list_cases()
        if not case.case_id.startswith("fixed-rag-") or case.case_id in current_fixed_ids
    ]
    query = q.strip().casefold()
    if query:
        # 搜索只作用于当前组织已持久化的脱敏字段；不搜索凭据、原始模型响应或日志。
        visible = [
            case for case in visible
            if query in case.case_id.casefold()
            or query in case.question.casefold()
            or query in case.expected_status.casefold()
            or any(query in tag.casefold() for tag in case.safety_tags)
        ]
    total = len(visible)
    start = (page - 1) * page_size
    page_items = visible[start : start + page_size]
    return EvaluationCasesPageResponse(
        items=[_response(case) for case in page_items], total=total, page=page,
        page_size=page_size, total_pages=max((total + page_size - 1) // page_size, 1),
        draft_count=sum(case.status == "draft" for case in visible),
        confirmed_count=sum(case.status == "confirmed" for case in visible),
    )


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
    """执行 confirm_evaluation_case 的业务流程并返回该流程的结果。"""
    case = await gateway.confirm_case(case_id, reviewer=payload.reviewer)
    if case is None:
        raise HTTPException(status_code=404, detail="评测案例不存在")
    return _response(case)


@router.post("/runs", response_model=dict[str, object], status_code=202)
async def start_evaluation(
    payload: EvaluationRunPayload,
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
) -> dict[str, object]:
    """执行 start_evaluation 的业务流程并返回该流程的结果。"""
    await gateway.seed_fixed_cases(_fixed_cases())
    limit = suite_case_limit(payload.suite)
    target_ids = fixed_suite_case_ids(payload.suite)
    cases = {case.case_id: case for case in await gateway.list_cases()}
    confirmed = [case_id for case_id in target_ids
                 if cases.get(case_id) is not None and cases[case_id].status == "confirmed"]
    gate_status: Literal["ready", "blocked"] = (
        "ready" if len(confirmed) == limit else "blocked"
    )
    if gate_status == "blocked":
        # 门禁未通过的点击只返回当前确认进度，不创建历史运行记录，避免重复点击污染报告。
        return {
            "run_id": None,
            "status": "blocked",
            "suite": payload.suite,
            "target_count": limit,
            "confirmed_count": len(confirmed),
            "case_ids": list(target_ids),
            "gate_status": gate_status,
            "deduplicated": False,
        }
    existing = await gateway.find_active_run(payload.suite)
    run_id = existing.run_id if existing is not None else await gateway.create_run(
        payload.suite, gate_status
    )
    current = existing or await gateway.get_run(run_id)
    return {
        "run_id": run_id,
        "status": current.status if current is not None else "queued", "suite": payload.suite,
        "target_count": limit, "confirmed_count": len(confirmed),
        "case_ids": list(target_ids),
        "gate_status": gate_status,
        "deduplicated": existing is not None,
    }


@router.post("/metrics", response_model=dict[str, object])
async def calculate_evaluation_metrics(
    observations: list[MetricObservationPayload],
) -> dict[str, object]:
    """执行 calculate_evaluation_metrics 的业务流程并返回该流程的结果。"""
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


@router.get("/runs", response_model=list[EvaluationRunResponse])
async def list_evaluation_runs(
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[EvaluationRunResponse]:
    """结果页读取当前组织的运行历史；不返回案例正文或模型原始响应。"""
    return [_run_response(run) for run in await gateway.list_runs(limit)]


@router.get("/runs/{run_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run(
    run_id: str,
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
) -> EvaluationRunResponse:
    """执行 get_evaluation_run 的业务流程并返回该流程的结果。"""
    run = await gateway.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="评测运行不存在或不可见")
    return _run_response(run)


@router.post("/runs/{run_id}/metrics", response_model=EvaluationRunResponse)
async def save_evaluation_run_metrics(
    run_id: str,
    observations: list[MetricObservationPayload],
    gateway: Annotated[RagEvaluationGateway, Depends(get_rag_evaluation_gateway)],
) -> EvaluationRunResponse:
    """由评测 Worker 回写聚合指标；只接受已通过启动门禁的运行。"""
    if not observations:
        raise HTTPException(status_code=422, detail="评测结果不能为空")
    calculated = await calculate_evaluation_metrics(observations)
    saved = await gateway.save_run_metrics(
        run_id,
        {key: value for key, value in calculated.items() if isinstance(value, (int, float, str))},
        len(observations), len(observations), 0, 0,
    )
    if saved is None:
        raise HTTPException(status_code=409, detail="评测运行未通过门禁或已完成")
    return _run_response(saved)
