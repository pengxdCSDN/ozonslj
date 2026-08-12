"""模型额度策略与用量台账的 PostgreSQL 适配器。

策略和用量属于组织级事实，必须通过事务和 ``ON CONFLICT`` 原子累加；这样
多个 RAG Worker 并发结算时不会覆盖彼此的 token 或请求次数。API Key、提示词
和模型原始响应不进入本表。
"""

from __future__ import annotations

from datetime import date
from typing import cast

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.model_budget import (
    BudgetPurpose,
    ModelBudgetPolicy,
    ModelBudgetUsage,
)


class PostgresModelBudgetGateway:
    """持久化用途级预算策略，并原子累计周期用量。"""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def upsert_policy(self, *, organization_id: str, policy: ModelBudgetPolicy) -> None:
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
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
                (
                    organization_id,
                    policy.provider_id,
                    policy.purpose,
                    policy.daily_token_limit,
                    policy.monthly_token_limit,
                    policy.daily_request_limit,
                    policy.monthly_budget,
                ),
            )

    async def get_policy(
        self, *, organization_id: str, provider_id: str, purpose: BudgetPurpose
    ) -> ModelBudgetPolicy | None:
        async with self._pool.connection() as connection, connection.cursor(
            row_factory=dict_row
        ) as cursor:
            await cursor.execute(
                """
                SELECT provider_id, purpose, daily_token_limit, monthly_token_limit,
                       daily_request_limit, monthly_budget
                FROM rag_model_budget_policies
                WHERE organization_id = %s AND provider_id = %s AND purpose = %s
                """,
                (organization_id, provider_id, purpose),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        values = cast(dict[str, object], row)
        return ModelBudgetPolicy(
            provider_id=str(values["provider_id"]),
            purpose=cast(BudgetPurpose, str(values["purpose"])),
            daily_token_limit=cast(int, values["daily_token_limit"]),
            monthly_token_limit=cast(int, values["monthly_token_limit"]),
            daily_request_limit=cast(int, values["daily_request_limit"]),
            monthly_budget=cast(float, values["monthly_budget"]),
        )

    async def add_usage(
        self,
        *,
        organization_id: str,
        provider_id: str,
        purpose: BudgetPurpose,
        period_start: date,
        daily_tokens: int,
        monthly_tokens: int,
        daily_requests: int,
        monthly_cost: float,
    ) -> None:
        if min(daily_tokens, monthly_tokens, daily_requests) < 0 or monthly_cost < 0:
            raise ValueError("额度用量增量不能为负数")
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
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
                (
                    organization_id,
                    provider_id,
                    purpose,
                    period_start,
                    daily_tokens,
                    monthly_tokens,
                    daily_requests,
                    monthly_cost,
                ),
            )

    async def get_usage(
        self,
        *,
        organization_id: str,
        provider_id: str,
        purpose: BudgetPurpose,
        period_start: date,
    ) -> ModelBudgetUsage:
        async with self._pool.connection() as connection, connection.cursor(
            row_factory=dict_row
        ) as cursor:
            await cursor.execute(
                """
                SELECT daily_tokens, monthly_tokens, daily_requests, monthly_cost
                FROM rag_model_budget_usage
                WHERE organization_id = %s AND provider_id = %s
                  AND purpose = %s AND period_start = %s
                """,
                (organization_id, provider_id, purpose, period_start),
            )
            row = await cursor.fetchone()
        if row is None:
            return ModelBudgetUsage(0, 0, 0, 0.0)
        values = cast(dict[str, object], row)
        return ModelBudgetUsage(
            daily_tokens=cast(int, values["daily_tokens"]),
            monthly_tokens=cast(int, values["monthly_tokens"]),
            daily_requests=cast(int, values["daily_requests"]),
            monthly_cost=cast(float, values["monthly_cost"]),
        )
