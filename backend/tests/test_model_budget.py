from backend.app.domain.model_budget import ModelBudgetPolicy, ModelBudgetUsage, decide_budget


def _policy() -> ModelBudgetPolicy:
    return ModelBudgetPolicy("p1", 1000, 10_000, 100, 100.0)


def test_budget_warning_at_ninety_percent() -> None:
    decision = decide_budget(_policy(), ModelBudgetUsage(900, 0, 0, 0))
    assert decision.state == "warning"
    assert decision.allowed is True


def test_budget_exceeded_blocks_request() -> None:
    decision = decide_budget(_policy(), ModelBudgetUsage(1000, 0, 0, 0))
    assert decision.state == "exceeded"
    assert decision.allowed is False
