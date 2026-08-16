"""模型供应商预算、配额和熔断决策。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BudgetState = Literal["normal", "warning", "exceeded"]
BudgetPurpose = Literal["embedding", "translation", "intent_rewrite", "rerank", "answer_generation"]


@dataclass(frozen=True, slots=True)
class ModelBudgetPolicy:
    provider_id: str
    daily_token_limit: int
    monthly_token_limit: int
    daily_request_limit: int
    monthly_budget: float
    purpose: BudgetPurpose = "answer_generation"


@dataclass(frozen=True, slots=True)
class ModelBudgetUsage:
    daily_tokens: int
    monthly_tokens: int
    daily_requests: int
    monthly_cost: float


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    state: BudgetState
    allowed: bool
    reason: str | None


def decide_budget(policy: ModelBudgetPolicy, usage: ModelBudgetUsage) -> BudgetDecision:
    ratios = [
        usage.daily_tokens / max(policy.daily_token_limit, 1),
        usage.monthly_tokens / max(policy.monthly_token_limit, 1),
        usage.daily_requests / max(policy.daily_request_limit, 1),
        usage.monthly_cost / max(policy.monthly_budget, 0.01),
    ]
    highest = max(ratios)
    if highest >= 1.0:
        return BudgetDecision("exceeded", False, "供应商配额已达到上限，已切换备用模型")
    if highest >= 0.9:
        return BudgetDecision("warning", True, "供应商配额已达到 90%，后续请求优先使用备用模型")
    return BudgetDecision("normal", True, None)
