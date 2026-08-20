"""模型供应商额度策略、用量台账和降级判定 API。"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_model_budget_gateway,
    require_account_manager,
)
from backend.app.domain.model_budget import (
    BudgetPurpose,
    ModelBudgetPolicy,
    ModelBudgetUsage,
    decide_budget,
)
from backend.app.infrastructure.postgres.model_budgets import PostgresModelBudgetGateway

router = APIRouter(prefix="/v1/model-budgets", tags=["model-budgets"])


class BudgetPolicyPayload(BaseModel):
    """管理员可配置的用途级预算边界；所有上限均拒绝非正数。"""

    daily_token_limit: int = Field(gt=0, le=10_000_000_000)
    monthly_token_limit: int = Field(gt=0, le=100_000_000_000)
    daily_request_limit: int = Field(gt=0, le=100_000_000)
    monthly_budget: float = Field(gt=0, le=100_000_000)
    # 第一阶段统一以人民币作为预算核算币种，避免页面出现无单位金额。
    budget_currency: Literal["RMB"] = "RMB"
    purpose: BudgetPurpose = "answer_generation"


class BudgetUsagePayload(BaseModel):
    """模型调用完成后结算的脱敏用量增量。"""

    daily_tokens: int = Field(ge=0)
    monthly_tokens: int = Field(ge=0)
    daily_requests: int = Field(ge=0)
    monthly_cost: float = Field(ge=0)


class BudgetMetricPayload(BaseModel):
    """向页面解释每一项预算的已用、上限和触发状态，避免只显示一个笼统的阻断。"""

    key: Literal["daily_tokens", "monthly_tokens", "daily_requests", "monthly_cost"]
    label: str
    used: float
    limit: float
    ratio: float
    state: Literal["normal", "warning", "exceeded"]


class BudgetResponse(BaseModel):
    """说明 BudgetResponse 的职责、状态边界和对外协作关系。"""
    provider_id: str
    purpose: BudgetPurpose
    policy: BudgetPolicyPayload
    usage: BudgetUsagePayload
    state: str
    allowed: bool
    reason: str | None
    metrics: list[BudgetMetricPayload]


def _response(
    provider_id: str, policy: ModelBudgetPolicy, usage: ModelBudgetUsage
) -> BudgetResponse:
    """执行内部步骤 _response，供同一模块的公开流程复用。"""
    decision = decide_budget(policy, usage)
    # 四项预算必须全部回传；用户需要知道到底是 Token、请求次数还是费用触发阻断。
    metric_values = [
        ("daily_tokens", "今日 Token", usage.daily_tokens, policy.daily_token_limit),
        ("monthly_tokens", "本月 Token", usage.monthly_tokens, policy.monthly_token_limit),
        ("daily_requests", "今日请求数", usage.daily_requests, policy.daily_request_limit),
        ("monthly_cost", "本月费用（RMB）", usage.monthly_cost, policy.monthly_budget),
    ]
    metrics = []
    for key, label, used, limit in metric_values:
        ratio = used / max(limit, 0.01)
        state = "exceeded" if ratio >= 1 else "warning" if ratio >= 0.9 else "normal"
        metrics.append(BudgetMetricPayload(
            key=key, label=label, used=used, limit=limit, ratio=ratio, state=state,
        ))
    return BudgetResponse(
        provider_id=provider_id,
        purpose=policy.purpose,
        policy=BudgetPolicyPayload(
            daily_token_limit=policy.daily_token_limit,
            monthly_token_limit=policy.monthly_token_limit,
            daily_request_limit=policy.daily_request_limit,
            monthly_budget=policy.monthly_budget,
            purpose=policy.purpose,
        ),
        usage=BudgetUsagePayload(
            daily_tokens=usage.daily_tokens,
            monthly_tokens=usage.monthly_tokens,
            daily_requests=usage.daily_requests,
            monthly_cost=usage.monthly_cost,
        ),
        state=decision.state,
        allowed=decision.allowed,
        reason=decision.reason,
        metrics=metrics,
    )


def _period_start() -> date:
    """按自然月读取用量；daily 字段由结算端在日切换时归零。"""
    today = date.today()
    return today.replace(day=1)


@router.put("/{provider_id}", response_model=BudgetResponse)
async def upsert_model_budget(
    provider_id: str,
    payload: BudgetPolicyPayload,
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresModelBudgetGateway, Depends(get_model_budget_gateway)],
) -> BudgetResponse:
    # 币种是接口层的显式契约字段，领域策略当前固定按 RMB 核算，不把它重复写入策略对象。
    """执行 upsert_model_budget 的业务流程并返回该流程的结果。"""
    policy = ModelBudgetPolicy(
        provider_id=provider_id,
        **payload.model_dump(exclude={"budget_currency"}),
    )
    await gateway.upsert_policy(policy=policy)
    usage = await gateway.get_usage(
        provider_id=provider_id,
        purpose=policy.purpose, period_start=_period_start(),
    )
    return _response(provider_id, policy, usage)


@router.get("", response_model=list[BudgetResponse])
async def list_model_budgets(
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresModelBudgetGateway, Depends(get_model_budget_gateway)],
) -> list[BudgetResponse]:
    """执行 list_model_budgets 的业务流程并返回该流程的结果。"""
    policies = await gateway.list_policies()
    return [
        _response(
            policy.provider_id,
            policy,
            await gateway.get_usage(
                provider_id=policy.provider_id,
                purpose=policy.purpose, period_start=_period_start(),
            ),
        )
        for policy in policies
    ]


@router.get("/{provider_id}", response_model=BudgetResponse)
async def get_model_budget(
    provider_id: str,
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresModelBudgetGateway, Depends(get_model_budget_gateway)],
    purpose: BudgetPurpose = "answer_generation",
) -> BudgetResponse:
    """执行 get_model_budget 的业务流程并返回该流程的结果。"""
    policy = await gateway.get_policy(provider_id=provider_id, purpose=purpose)
    if policy is None:
        raise HTTPException(status_code=404, detail="供应商额度策略不存在")
    usage = await gateway.get_usage(
        provider_id=provider_id,
        purpose=purpose, period_start=_period_start(),
    )
    return _response(provider_id, policy, usage)


@router.post("/{provider_id}/evaluate", response_model=BudgetResponse)
async def evaluate_model_budget(
    provider_id: str,
    payload: BudgetUsagePayload,
    gateway: Annotated[PostgresModelBudgetGateway, Depends(get_model_budget_gateway)],
    purpose: BudgetPurpose = "answer_generation",
) -> BudgetResponse:
    """执行 evaluate_model_budget 的业务流程并返回该流程的结果。"""
    policy = await gateway.get_policy(provider_id=provider_id, purpose=purpose)
    if policy is None:
        raise HTTPException(status_code=404, detail="供应商额度策略不存在")
    await gateway.add_usage(
        provider_id=provider_id, purpose=purpose,
        period_start=_period_start(), **payload.model_dump(),
    )
    usage = await gateway.get_usage(
        provider_id=provider_id,
        purpose=purpose, period_start=_period_start(),
    )
    return _response(provider_id, policy, usage)
