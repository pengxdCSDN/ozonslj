"""固定 RAG 评测执行器。

执行器只依赖知识问答引擎端口，按固定案例清单串行、每批最多 10 例运行，
将异常和未执行案例排除在通过分母之外并明确报告。它不保存问题正文、模型原始响应
或凭据；持久化由上层评测任务适配器负责。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
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
    for start in range(0, len(selected), batch_size):
        for case in selected[start : start + batch_size]:
            try:
                started = time.perf_counter()
                answers = await engine.answer(case.question, limit=10)
                latency_ms = round((time.perf_counter() - started) * 1000)
                observations.append(_observation(case, answers, latency_ms))
            except Exception as error:
                # 评测报告不能保存供应商原始错误；仅记录稳定的异常类型。
                del error
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
    )


def _observation(
    case: FixedEvaluationCase,
    answers: tuple[KnowledgeSegmentAnswer, ...],
    latency_ms: int,
) -> EvaluationObservation:
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
