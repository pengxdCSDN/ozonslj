from backend.app.domain.rag_metrics import (
    EvaluationObservation,
    calculate_metrics,
    quality_gate_passed,
)


def test_metrics_are_bounded_and_refusal_is_counted() -> None:
    metrics = calculate_metrics(
        [
            EvaluationObservation(
                frozenset({"a"}), frozenset({"a", "b"}), frozenset({"a"}),
                "answered", "answered", 10, 0.2,
            ),
            EvaluationObservation(
                frozenset(), frozenset(), frozenset(), "unsupported", "unsupported", 20, 0.1,
            ),
        ]
    )
    assert metrics.recall == 1.0
    assert metrics.precision == 0.5
    assert metrics.citation_support_rate == 1.0
    assert metrics.correct_refusal_rate == 1.0
    assert metrics.average_latency_ms == 15
    assert metrics.recall_at_5 == 1.0
    assert not quality_gate_passed(metrics)
