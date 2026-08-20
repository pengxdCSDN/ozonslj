"""固定 RAG 评测执行器。

执行器只依赖知识问答引擎端口，按固定案例清单串行、每批最多 10 例运行，
将异常和未执行案例排除在通过分母之外并明确报告。它不保存问题正文、模型原始响应
或凭据；持久化由上层评测任务适配器负责。
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from backend.app.domain.knowledge_query import KnowledgeQueryEngine, KnowledgeSegmentAnswer
from backend.app.domain.rag_evaluation_corpus import (
    FixedEvaluationCase,
    fixed_evaluation_corpus,
    fixed_suite_case_ids,
)
from backend.app.domain.rag_metrics import (
    EvaluationObservation,
    RagQualityMetrics,
    calculate_metrics,
)

ERROR_LABELS: dict[str, str] = {
    "embedding_unavailable": "Embedding 供应商不可用",
    "embedding_dimension_mismatch": "Embedding 向量维度不一致",
    "chroma_unavailable": "Chroma 检索不可用",
    "reranker_unavailable": "Reranker 供应商不可用",
    "text_model_unavailable": "文本模型不可用",
    "quota_exceeded": "供应商限流或额度不足",
    "timeout": "供应商请求超时",
    "model_not_found": "模型或接口不存在",
    "unauthorized": "供应商认证失败",
    "provider_request_failed": "供应商请求失败",
    "invalid_response": "供应商响应格式无效",
    "runtime_error": "RAG 运行时错误",
}

SuiteName = Literal["quick", "standard", "full"]
RunStatus = Literal["completed", "partial", "error"]


@dataclass(frozen=True, slots=True)
class QualityRunReport:
    """一次固定评测的脱敏汇总；错误只保留案例 ID 和错误类别。"""

    suite: SuiteName
    target_count: int
    executed_count: int
    error_count: int
    status: RunStatus
    metrics: RagQualityMetrics
    error_case_ids: tuple[str, ...]
    error_breakdown: dict[str, int] = field(default_factory=dict)
    primary_error_code: str | None = None


async def run_fixed_quality_suite(
    engine: KnowledgeQueryEngine,
    suite: SuiteName,
    *,
    cases: tuple[FixedEvaluationCase, ...] | None = None,
    batch_size: int = 10,
) -> QualityRunReport:
    """执行 quick/standard/full 固定集，不随机抽样、不并发轰击模型供应商。"""

    if batch_size < 1 or batch_size > 10:
        raise ValueError("评测批次必须在 1 到 10 之间")
    corpus = cases or fixed_evaluation_corpus()
    selected_ids = fixed_suite_case_ids(suite)
    by_id = {case.case_id: case for case in corpus}
    selected = [by_id[case_id] for case_id in selected_ids if case_id in by_id]
    observations: list[EvaluationObservation] = []
    errors: list[str] = []
    error_breakdown: Counter[str] = Counter()
    primary_error_code: str | None = None
    for start in range(0, len(selected), batch_size):
        for case in selected[start : start + batch_size]:
            try:
                started = time.perf_counter()
                answers = await engine.answer(case.question, limit=10)
                chain_errors = {
                    answer.reason for answer in answers
                    if answer.reason in {"reranker_unavailable", "text_model_unavailable"}
                }
                if chain_errors:
                    raise RuntimeError(next(iter(chain_errors)))
                latency_ms = round((time.perf_counter() - started) * 1000)
                observations.append(_observation(case, answers, latency_ms))
            except Exception as error:
                # 评测报告不能保存供应商原始错误；只保留稳定的脱敏分类，
                # 让结果页能区分维度、限流、认证、超时和服务不可用。
                code = classify_evaluation_error(error)
                error_breakdown[code] += 1
                primary_error_code = primary_error_code or code
                errors.append(case.case_id)
    target_count = len(selected_ids)
    executed_count = len(observations)
    status: RunStatus = "completed" if not errors and executed_count == target_count else (
        "partial" if executed_count else "error"
    )
    return QualityRunReport(
        suite=suite,
        target_count=target_count,
        executed_count=executed_count,
        error_count=len(errors),
        status=status,
        metrics=calculate_metrics(observations),
        error_case_ids=tuple(errors),
        error_breakdown=dict(error_breakdown),
        primary_error_code=primary_error_code,
    )


def classify_evaluation_error(error: BaseException) -> str:
    """将供应商/基础设施异常归一为可展示的脱敏错误码。"""

    chain: list[BaseException] = []
    current: BaseException | None = error
    while current is not None and len(chain) < 5:
        chain.append(current)
        current = current.__cause__ or current.__context__
    text = " ".join(str(item).casefold() for item in chain)
    type_names = " ".join(type(item).__name__ for item in chain).casefold()
    if "timeout" in type_names or "timeout" in text:
        return "timeout"
    if "notfound" in type_names or "model_not_found" in text or "模型或接口不存在" in text:
        return "model_not_found"
    if "quota" in type_names or "429" in text or "限流" in text or "额度" in text:
        return "quota_exceeded"
    if "401" in text or "403" in text or "认证" in text or "credential" in text:
        return "unauthorized"
    if "维度" in text or "dimension" in text:
        return "embedding_dimension_mismatch"
    if "embedding" in text or "向量供应商" in text:
        return "embedding_unavailable"
    if "chroma" in text:
        return "chroma_unavailable"
    if "rerank" in text or "重排序" in text:
        return "reranker_unavailable"
    if "text model" in text or "文本模型" in text:
        return "text_model_unavailable"
    if "json" in text or "response" in text or "响应" in text:
        return "invalid_response"
    if "http" in text or "network" in text or "供应商" in text:
        return "provider_request_failed"
    return "runtime_error"


def _observation(
    case: FixedEvaluationCase,
    answers: tuple[KnowledgeSegmentAnswer, ...],
    latency_ms: int,
) -> EvaluationObservation:
    """执行内部步骤 _observation，供同一模块的公开流程复用。"""
    statuses = {answer.status for answer in answers}
    actual_status = (
        "partially_answered" if len(statuses) > 1 else next(iter(statuses), "unsupported")
    )
    citations = tuple(citation.chunk_id for answer in answers for citation in answer.citations)
    expected = frozenset(case.expected_chunk_ids)
    safety_case = bool(set(case.safety_tags) & {"prompt_injection", "permission_boundary"})
    safety_passed = not safety_case or actual_status == case.expected_status
    multi_intent_complete = "multi_intent" not in case.safety_tags or len(answers) > 1
    return EvaluationObservation(
        expected_chunk_ids=expected,
        retrieved_chunk_ids=frozenset(citations),
        cited_chunk_ids=frozenset(citations),
        expected_status=case.expected_status,
        actual_status=actual_status,
        latency_ms=latency_ms,
        estimated_cost=0.0,
        ranked_retrieved_chunk_ids=citations,
        multi_intent_complete=multi_intent_complete,
        safety_passed=safety_passed,
    )
