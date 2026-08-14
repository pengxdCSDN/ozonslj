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


class BudgetResponse(BaseModel):
    provider_id: str
    purpose: BudgetPurpose
    policy: BudgetPolicyPayload
    usage: BudgetUsagePayload
    state: str
    allowed: bool
    reason: str | None


def _response(
    provider_id: str, policy: ModelBudgetPolicy, usage: ModelBudgetUsage
) -> BudgetResponse:
    decision = decide_budget(policy, usage)
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
