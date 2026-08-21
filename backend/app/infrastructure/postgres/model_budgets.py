"""模型额度策略与用量台账的 PostgreSQL 适配器。

额度是组织级治理事实，所有查询都通过带 RLS 上下文的短事务执行；用量结算使用
数据库原子累加，避免多个 API/Worker 并发时覆盖彼此的 token 和请求次数。
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from typing import cast

from backend.app.domain.model_budget import BudgetPurpose, ModelBudgetPolicy, ModelBudgetUsage
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresModelBudgetGateway:
    """按租户持久化用途级预算策略，并安全累计当前周期用量。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def upsert_policy(self, *, policy: ModelBudgetPolicy) -> None:
        """执行 upsert_policy 的业务流程并返回该流程的结果。

Args:
    policy: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        await asyncio.to_thread(self._upsert_policy, policy)

    def _upsert_policy(self, policy: ModelBudgetPolicy) -> None:
        """执行内部步骤 _upsert_policy，供同一模块的公开流程复用。

Args:
    policy: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO rag_model_budget_policies
                    (organization_id, provider_id, purpose, daily_token_limit,
                     monthly_token_limit, daily_request_limit, monthly_budget)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, provider_id, purpose) DO UPDATE SET
                    daily_token_limit = EXCLUDED.daily_token_limit,
                    monthly_token_limit = EXCLUDED.monthly_token_limit,
                    daily_request_limit = EXCLUDED.daily_request_limit,
                    monthly_budget = EXCLUDED.monthly_budget,
                    revision = rag_model_budget_policies.revision + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (self._context.organization_id, policy.provider_id, policy.purpose,
                 policy.daily_token_limit, policy.monthly_token_limit,
                 policy.daily_request_limit, policy.monthly_budget),
            )

    async def list_policies(self) -> list[ModelBudgetPolicy]:
        """执行 list_policies 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_policies)

    def _list_policies(self) -> list[ModelBudgetPolicy]:
        """执行内部步骤 _list_policies，供同一模块的公开流程复用。
Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT provider_id, purpose, daily_token_limit, monthly_token_limit,
                       daily_request_limit, monthly_budget
                FROM rag_model_budget_policies
                WHERE organization_id = %s
                ORDER BY provider_id, purpose
                """,
                (self._context.organization_id,),
            ).fetchall()
        return [_policy_from_row(row) for row in rows]

    async def get_policy(
        self, *, provider_id: str, purpose: BudgetPurpose
    ) -> ModelBudgetPolicy | None:
        """执行 get_policy 的业务流程并返回该流程的结果。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._get_policy, provider_id, purpose)

    def _get_policy(self, provider_id: str, purpose: BudgetPurpose) -> ModelBudgetPolicy | None:
        """执行内部步骤 _get_policy，供同一模块的公开流程复用。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                SELECT provider_id, purpose, daily_token_limit, monthly_token_limit,
                       daily_request_limit, monthly_budget
                FROM rag_model_budget_policies
                WHERE organization_id = %s AND provider_id = %s AND purpose = %s
                """,
                (self._context.organization_id, provider_id, purpose),
            ).fetchone()
        return _policy_from_row(row) if row is not None else None

    async def add_usage(self, *, provider_id: str, purpose: BudgetPurpose,
                        period_start: date, daily_tokens: int, monthly_tokens: int,
                        daily_requests: int, monthly_cost: float) -> None:
        """执行 add_usage 的业务流程并返回该流程的结果。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。
    period_start: 参数语义、输入边界和安全约束。
    daily_tokens: 参数语义、输入边界和安全约束。
    monthly_tokens: 参数语义、输入边界和安全约束。
    daily_requests: 参数语义、输入边界和安全约束。
    monthly_cost: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
        if min(daily_tokens, monthly_tokens, daily_requests) < 0 or monthly_cost < 0:
            raise ValueError("额度用量增量不能为负数")
        await asyncio.to_thread(
            self._add_usage, provider_id, purpose, period_start,
            daily_tokens, monthly_tokens, daily_requests, monthly_cost,
        )

    def _add_usage(self, provider_id: str, purpose: BudgetPurpose, period_start: date,
                   daily_tokens: int, monthly_tokens: int, daily_requests: int,
                   monthly_cost: float) -> None:
        """执行内部步骤 _add_usage，供同一模块的公开流程复用。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。
    period_start: 参数语义、输入边界和安全约束。
    daily_tokens: 参数语义、输入边界和安全约束。
    monthly_tokens: 参数语义、输入边界和安全约束。
    daily_requests: 参数语义、输入边界和安全约束。
    monthly_cost: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO rag_model_budget_usage
                    (organization_id, provider_id, purpose, period_start,
                     daily_tokens, monthly_tokens, daily_requests, monthly_cost)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, provider_id, purpose, period_start)
                DO UPDATE SET
                    daily_tokens = rag_model_budget_usage.daily_tokens + EXCLUDED.daily_tokens,
                    monthly_tokens = rag_model_budget_usage.monthly_tokens
                        + EXCLUDED.monthly_tokens,
                    daily_requests = rag_model_budget_usage.daily_requests
                        + EXCLUDED.daily_requests,
                    monthly_cost = rag_model_budget_usage.monthly_cost + EXCLUDED.monthly_cost,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (self._context.organization_id, provider_id, purpose, period_start,
                 daily_tokens, monthly_tokens, daily_requests, monthly_cost),
            )

    async def get_usage(self, *, provider_id: str, purpose: BudgetPurpose,
                        period_start: date) -> ModelBudgetUsage:
        """执行 get_usage 的业务流程并返回该流程的结果。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。
    period_start: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._get_usage, provider_id, purpose, period_start)

    def _get_usage(self, provider_id: str, purpose: BudgetPurpose,
                   period_start: date) -> ModelBudgetUsage:
        """执行内部步骤 _get_usage，供同一模块的公开流程复用。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    purpose: 参数语义、输入边界和安全约束。
    period_start: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                SELECT
                    COALESCE(SUM(daily_tokens) FILTER (WHERE period_start = %s), 0) AS daily_tokens,
                    COALESCE(SUM(monthly_tokens), 0) AS monthly_tokens,
                    COALESCE(
                        SUM(daily_requests) FILTER (WHERE period_start = %s), 0
                    ) AS daily_requests,
                    COALESCE(SUM(monthly_cost), 0) AS monthly_cost
                FROM rag_model_budget_usage
                WHERE organization_id = %s AND provider_id = %s
                  AND purpose = %s
                  AND period_start >= %s
                  AND period_start < (%s + INTERVAL '1 month')::date
                """,
                (period_start, period_start, self._context.organization_id, provider_id,
                 purpose, period_start.replace(day=1)),
            ).fetchone()
        if row is None:
            return ModelBudgetUsage(0, 0, 0, 0.0)
        return ModelBudgetUsage(
            daily_tokens=cast(int, row["daily_tokens"]),
            monthly_tokens=cast(int, row["monthly_tokens"]),
            daily_requests=cast(int, row["daily_requests"]),
            # PostgreSQL NUMERIC 会由 psycopg 返回 Decimal；领域层预算计算统一使用 float，
            # 这里是数据库边界的显式归一化，避免 Decimal 与 float 运算触发 500。
            monthly_cost=float(str(cast(Decimal, row["monthly_cost"]))),
        )


def _policy_from_row(row: object) -> ModelBudgetPolicy:
    """执行内部步骤 _policy_from_row，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    values = cast(dict[str, object], row)
    return ModelBudgetPolicy(
        provider_id=str(values["provider_id"]), purpose=cast(BudgetPurpose, str(values["purpose"])),
        daily_token_limit=cast(int, values["daily_token_limit"]),
        monthly_token_limit=cast(int, values["monthly_token_limit"]),
        daily_request_limit=cast(int, values["daily_request_limit"]),
        # PostgreSQL NUMERIC 的预算金额同样可能是 Decimal；领域层统一按 float 计算比例。
        monthly_budget=float(str(values["monthly_budget"])),
    )
