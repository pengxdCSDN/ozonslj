"""模型额度 API 的策略持久化边界与降级决策测试。"""

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_model_budget_gateway, require_account_manager
from backend.app.api.routes.model_budgets import router
from backend.app.domain.model_budget import ModelBudgetPolicy, ModelBudgetUsage


class MemoryBudgetGateway:
    """仅用于 API 单元测试的异步替身；生产路由使用 PostgreSQL 网关。"""

    def __init__(self) -> None:
        self.policies: dict[tuple[str, str], ModelBudgetPolicy] = {}
        self.usage: dict[tuple[str, str], ModelBudgetUsage] = {}

    async def upsert_policy(self, *, policy: ModelBudgetPolicy) -> None:
        self.policies[(policy.provider_id, policy.purpose)] = policy

    async def list_policies(self) -> list[ModelBudgetPolicy]:
        return list(self.policies.values())

    async def get_policy(self, *, provider_id: str, purpose: str) -> ModelBudgetPolicy | None:
        return self.policies.get((provider_id, purpose))

    async def get_usage(
        self, *, provider_id: str, purpose: str, period_start: date
    ) -> ModelBudgetUsage:
        return self.usage.get((provider_id, purpose), ModelBudgetUsage(0, 0, 0, 0.0))

    async def add_usage(
        self, *, provider_id: str, purpose: str, period_start: date,
        **values: int | float
    ) -> None:
        current = await self.get_usage(
            provider_id=provider_id, purpose=purpose, period_start=period_start
        )
        self.usage[(provider_id, purpose)] = ModelBudgetUsage(
            current.daily_tokens + int(values["daily_tokens"]),
            current.monthly_tokens + int(values["monthly_tokens"]),
            current.daily_requests + int(values["daily_requests"]),
            current.monthly_cost + float(values["monthly_cost"]),
        )


def make_client() -> tuple[TestClient, MemoryBudgetGateway]:
    app = FastAPI()
    gateway = MemoryBudgetGateway()
    app.dependency_overrides[get_model_budget_gateway] = lambda: gateway
    app.dependency_overrides[require_account_manager] = lambda: object()
    app.include_router(router)
    return TestClient(app), gateway


def test_budget_api_returns_warning_then_exceeded() -> None:
    client, _ = make_client()
    configured = client.put(
        "/v1/model-budgets/provider-budget-api",
        json={"daily_token_limit": 100, "monthly_token_limit": 1000,
              "daily_request_limit": 10, "monthly_budget": 100},
    )
    assert configured.status_code == 200
    warning = client.post(
        "/v1/model-budgets/provider-budget-api/evaluate",
        json={"daily_tokens": 90, "monthly_tokens": 200, "daily_requests": 1, "monthly_cost": 1},
    )
    assert warning.json()["state"] == "warning"
    exceeded = client.post(
        "/v1/model-budgets/provider-budget-api/evaluate",
        json={"daily_tokens": 11, "monthly_tokens": 200, "daily_requests": 1, "monthly_cost": 1},
    )
    assert exceeded.json()["state"] == "exceeded"
    assert exceeded.json()["allowed"] is False


def test_budget_api_hides_unknown_provider() -> None:
    client, _ = make_client()
    assert client.get("/v1/model-budgets/missing").status_code == 404


def test_budget_api_keeps_purpose_budgets_separate() -> None:
    client, _ = make_client()
    for purpose in ("embedding", "answer_generation"):
        response = client.put(
            "/v1/model-budgets/provider-purpose",
            json={"daily_token_limit": 100, "monthly_token_limit": 1000,
                  "daily_request_limit": 10, "monthly_budget": 100, "purpose": purpose},
        )
        assert response.json()["purpose"] == purpose
    assert client.get("/v1/model-budgets").json().__len__() == 2
