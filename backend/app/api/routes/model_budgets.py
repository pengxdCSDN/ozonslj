"""模型供应商额度策略与降级判定接口。

该路由只保存当前开发环境的内存状态，生产环境应由 PostgreSQL 迁移
``0094_rag_model_budgets.sql`` 对应的仓储实现替换。响应返回决策与脱敏
的额度信息，不返回 API Key 或其它凭据。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.model_budget import (
    BudgetPurpose,
    ModelBudgetPolicy,
    ModelBudgetUsage,
    decide_budget,
)

router = APIRouter(prefix="/v1/model-budgets", tags=["model-budgets"])
_policies: dict[str, ModelBudgetPolicy] = {}
_usage: dict[str, ModelBudgetUsage] = {}


class BudgetPolicyPayload(BaseModel):
    """供应商额度策略；所有上限必须为正数，避免零上限误触发除零。"""

    daily_token_limit: int = Field(gt=0, le=10_000_000_000)
    monthly_token_limit: int = Field(gt=0, le=100_000_000_000)
    daily_request_limit: int = Field(gt=0, le=100_000_000)
    monthly_budget: float = Field(gt=0, le=100_000_000)
    purpose: BudgetPurpose = Field(
        default="answer_generation",
        pattern="^(embedding|intent_rewrite|rerank|answer_generation)$",
    )


class BudgetUsagePayload(BaseModel):
    """供应商当前周期用量；用量不能为负数。"""

    daily_tokens: int = Field(ge=0)
    monthly_tokens: int = Field(ge=0)
    daily_requests: int = Field(ge=0)
    monthly_cost: float = Field(ge=0)


class BudgetResponse(BaseModel):
    provider_id: str
    purpose: BudgetPurpose
    policy: BudgetPolicyPayload
    usage: BudgetUsagePayload
    state: str
    allowed: bool
    reason: str | None


def _policy_key(provider_id: str, purpose: BudgetPurpose) -> str:
    return f"{provider_id}:{purpose}"


def _policy_payload(policy: ModelBudgetPolicy) -> BudgetPolicyPayload:
    return BudgetPolicyPayload(
        daily_token_limit=policy.daily_token_limit,
        monthly_token_limit=policy.monthly_token_limit,
        daily_request_limit=policy.daily_request_limit,
        monthly_budget=policy.monthly_budget,
        purpose=policy.purpose,
    )


def _usage_payload(usage: ModelBudgetUsage) -> BudgetUsagePayload:
    return BudgetUsagePayload(
        daily_tokens=usage.daily_tokens,
        monthly_tokens=usage.monthly_tokens,
        daily_requests=usage.daily_requests,
        monthly_cost=usage.monthly_cost,
    )


def _response(
    provider_id: str, policy: ModelBudgetPolicy, usage: ModelBudgetUsage
) -> BudgetResponse:
    decision = decide_budget(policy, usage)
    return BudgetResponse(
        provider_id=provider_id,
        purpose=policy.purpose,
        policy=_policy_payload(policy),
        usage=_usage_payload(usage),
        state=decision.state,
        allowed=decision.allowed,
        reason=decision.reason,
    )


@router.put("/{provider_id}", response_model=BudgetResponse)
async def upsert_model_budget(
    provider_id: str, payload: BudgetPolicyPayload
) -> BudgetResponse:
    """保存供应商策略，并以当前用量立即返回一次决策。"""

    policy = ModelBudgetPolicy(provider_id=provider_id, **payload.model_dump())
    policy_key = _policy_key(provider_id, policy.purpose)
    _policies[policy_key] = policy
    usage = _usage.get(policy_key, ModelBudgetUsage(0, 0, 0, 0.0))
    return _response(provider_id, policy, usage)


@router.get("", response_model=list[BudgetResponse])
async def list_model_budgets() -> list[BudgetResponse]:
    """列出已配置策略，便于管理页展示供应商健康状态。"""

    return [
        _response(
            policy.provider_id, policy,
            _usage.get(policy_key, ModelBudgetUsage(0, 0, 0, 0.0)),
        )
        for policy_key, policy in _policies.items()
    ]


@router.get("/{provider_id}", response_model=BudgetResponse)
async def get_model_budget(
    provider_id: str, purpose: BudgetPurpose = "answer_generation"
) -> BudgetResponse:
    policy_key = _policy_key(provider_id, purpose)
    policy = _policies.get(policy_key)
    if policy is None:
        raise HTTPException(status_code=404, detail="供应商额度策略不存在")
    usage = _usage.get(policy_key, ModelBudgetUsage(0, 0, 0, 0.0))
    return _response(provider_id, policy, usage)


@router.post("/{provider_id}/evaluate", response_model=BudgetResponse)
async def evaluate_model_budget(
    provider_id: str, payload: BudgetUsagePayload, purpose: BudgetPurpose = "answer_generation"
) -> BudgetResponse:
    """写入供应商用量并返回决策；exceeded 会明确拒绝当前供应商。"""

    policy_key = _policy_key(provider_id, purpose)
    policy = _policies.get(policy_key)
    if policy is None:
        raise HTTPException(status_code=404, detail="供应商额度策略不存在")
    usage = ModelBudgetUsage(**payload.model_dump())
    _usage[policy_key] = usage
    return _response(provider_id, policy, usage)
