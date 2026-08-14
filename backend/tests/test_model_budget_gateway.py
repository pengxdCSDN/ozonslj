"""模型预算网关的 SQL 结构回归测试，不连接真实 PostgreSQL。"""

from pathlib import Path


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
