"""RAG 质量指标计算：检索、引用支持、正确拒答、延迟和成本。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationObservation:
    expected_chunk_ids: frozenset[str]
    retrieved_chunk_ids: frozenset[str]
    cited_chunk_ids: frozenset[str]
    expected_status: str
    actual_status: str
    latency_ms: int
    estimated_cost: float


@dataclass(frozen=True, slots=True)
class RagQualityMetrics:
    recall: float
    precision: float
    citation_support_rate: float
    correct_refusal_rate: float
    average_latency_ms: float
    estimated_cost: float


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
    return RagQualityMetrics(
        recall=recalled / expected if expected else 0.0,
        precision=recalled / retrieved if retrieved else 0.0,
        citation_support_rate=cited / sum(len(item.cited_chunk_ids) for item in observations)
        if sum(len(item.cited_chunk_ids) for item in observations)
        else 0.0,
        correct_refusal_rate=refusal_correct / refusal_total if refusal_total else 0.0,
        average_latency_ms=sum(item.latency_ms for item in observations) / len(observations),
        estimated_cost=sum(item.estimated_cost for item in observations),
    )
