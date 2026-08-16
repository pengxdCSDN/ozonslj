"""模型预算网关的 SQL 结构回归测试，不连接真实 PostgreSQL。"""

from decimal import Decimal
from pathlib import Path

from backend.app.infrastructure.postgres.model_budgets import _policy_from_row


def test_budget_migration_and_gateway_use_purpose_scoped_atomic_usage() -> None:
    migration = Path("database/migrations/0094_rag_model_budgets.sql").read_text(
        encoding="utf-8"
    )
    gateway = Path("backend/app/infrastructure/postgres/model_budgets.py").read_text(
        encoding="utf-8"
    )
    assert "PRIMARY KEY (organization_id, provider_id, purpose, period_start)" in migration
    assert "ON CONFLICT (organization_id, provider_id, purpose, period_start)" in gateway
    assert "daily_tokens = rag_model_budget_usage.daily_tokens + EXCLUDED.daily_tokens" in gateway
    assert "monthly_cost = rag_model_budget_usage.monthly_cost + EXCLUDED.monthly_cost" in gateway


def test_budget_policy_normalizes_postgres_numeric_monthly_cost() -> None:
    """PostgreSQL NUMERIC 的 Decimal 值必须在网关边界转换为领域层 float。"""
    policy = _policy_from_row({
        "provider_id": "provider-1",
        "purpose": "answer_generation",
        "daily_token_limit": 100,
        "monthly_token_limit": 1000,
        "daily_request_limit": 10,
        "monthly_budget": Decimal("12.50"),
    })

    assert policy.monthly_budget == 12.5
    assert isinstance(policy.monthly_budget, float)
