"""RAG 质量指标计算：检索、引用支持、正确拒答、延迟和成本。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationObservation:
    """说明 EvaluationObservation 的职责、状态边界和对外协作关系。"""
    expected_chunk_ids: frozenset[str]
    retrieved_chunk_ids: frozenset[str]
    cited_chunk_ids: frozenset[str]
    expected_status: str
    actual_status: str
    latency_ms: int
    estimated_cost: float
    ranked_retrieved_chunk_ids: tuple[str, ...] = ()
    multi_intent_complete: bool = True
    safety_passed: bool = True
    degradation_expected: bool = False
    degradation_observed: bool = False


@dataclass(frozen=True, slots=True)
class RagQualityMetrics:
    """说明 RagQualityMetrics 的职责、状态边界和对外协作关系。"""
    recall: float
    precision: float
    citation_support_rate: float
    correct_refusal_rate: float
    average_latency_ms: float
    estimated_cost: float
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    precision_at_5: float = 0.0
    multi_intent_completeness: float = 0.0
    safety_pass_rate: float = 0.0
    degradation_pass_rate: float = 0.0


def quality_gate_passed(metrics: RagQualityMetrics) -> bool:
    """应用进入 pilot 前的硬门槛；安全和状态完整性必须 100%。"""

    return (
        metrics.recall_at_5 >= 0.95
        and metrics.recall_at_10 >= 0.85
        and metrics.precision_at_5 >= 0.70
        and metrics.citation_support_rate >= 0.95
        and metrics.correct_refusal_rate >= 0.95
        and metrics.multi_intent_completeness >= 1.0
        and metrics.safety_pass_rate >= 1.0
        and metrics.degradation_pass_rate >= 1.0
    )


def calculate_metrics(observations: list[EvaluationObservation]) -> RagQualityMetrics:
    """空样本返回零指标；不把 skipped/error 当作通过。"""

    if not observations:
        return RagQualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    expected = sum(len(item.expected_chunk_ids) for item in observations)
    retrieved = sum(len(item.retrieved_chunk_ids) for item in observations)
    recalled = sum(len(item.expected_chunk_ids & item.retrieved_chunk_ids) for item in observations)
    cited = sum(len(item.cited_chunk_ids & item.retrieved_chunk_ids) for item in observations)
    refusal_total = sum(item.expected_status in {"refused", "unsupported"} for item in observations)
    refusal_correct = sum(
        item.expected_status in {"refused", "unsupported"}
        and item.actual_status == item.expected_status
        for item in observations
    )
    ranked = [item.ranked_retrieved_chunk_ids or tuple(sorted(item.retrieved_chunk_ids))
              for item in observations]
    def recall_at(limit: int) -> float:
        """执行 recall_at 的业务流程并返回该流程的结果。"""
        denominator = sum(bool(item.expected_chunk_ids) for item in observations)
        hits = sum(
            bool(item.expected_chunk_ids & set(items[:limit]))
            for item, items in zip(observations, ranked, strict=True)
        )
        return hits / denominator if denominator else 0.0
    precision_top5 = sum(
        len(item.expected_chunk_ids & set(items[:5])) / min(5, len(items))
        for item, items in zip(observations, ranked, strict=True) if items
    ) / sum(bool(items) for items in ranked) if any(ranked) else 0.0
    safety_pass = sum(item.safety_passed for item in observations) / len(observations)
    multi_intent = sum(item.multi_intent_complete for item in observations) / len(observations)
    degradation_cases = [item for item in observations if item.degradation_expected]
    degradation = (
        sum(item.degradation_observed for item in degradation_cases) / len(degradation_cases)
        if degradation_cases else 1.0
    )
    return RagQualityMetrics(
        recall=recalled / expected if expected else 0.0,
        precision=recalled / retrieved if retrieved else 0.0,
        citation_support_rate=cited / sum(len(item.cited_chunk_ids) for item in observations)
        if sum(len(item.cited_chunk_ids) for item in observations)
        else 0.0,
        correct_refusal_rate=refusal_correct / refusal_total if refusal_total else 0.0,
        average_latency_ms=sum(item.latency_ms for item in observations) / len(observations),
        estimated_cost=sum(item.estimated_cost for item in observations),
        recall_at_5=recall_at(5), recall_at_10=recall_at(10),
        precision_at_5=precision_top5, multi_intent_completeness=multi_intent,
        safety_pass_rate=safety_pass, degradation_pass_rate=degradation,
    )
