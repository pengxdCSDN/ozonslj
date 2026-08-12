"""模型额度策略 API 的边界与降级决策测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.model_budgets import router


def test_budget_api_returns_warning_then_exceeded() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    provider_id = "provider-budget-api"
    configured = client.put(
        f"/v1/model-budgets/{provider_id}",
        json={
            "daily_token_limit": 100,
            "monthly_token_limit": 1000,
            "daily_request_limit": 10,
            "monthly_budget": 100,
        },
    )
    assert configured.status_code == 200
    assert configured.json()["state"] == "normal"

    warning = client.post(
        f"/v1/model-budgets/{provider_id}/evaluate",
        json={
            "daily_tokens": 90,
            "monthly_tokens": 200,
            "daily_requests": 1,
            "monthly_cost": 1,
        },
    )
    assert warning.json()["state"] == "warning"
    assert warning.json()["allowed"] is True

    exceeded = client.post(
        f"/v1/model-budgets/{provider_id}/evaluate",
        json={
            "daily_tokens": 101,
            "monthly_tokens": 200,
            "daily_requests": 1,
            "monthly_cost": 1,
        },
    )
    assert exceeded.json()["state"] == "exceeded"
    assert exceeded.json()["allowed"] is False


def test_budget_api_hides_unknown_provider() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/v1/model-budgets/missing").status_code == 404


def test_budget_api_keeps_purpose_budgets_separate() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    for purpose in ("embedding", "answer_generation"):
        response = client.put(
            "/v1/model-budgets/provider-purpose",
            json={
                "daily_token_limit": 100,
                "monthly_token_limit": 1000,
                "daily_request_limit": 10,
                "monthly_budget": 100,
                "purpose": purpose,
            },
        )
        assert response.json()["purpose"] == purpose
    assert client.get(
        "/v1/model-budgets/provider-purpose?purpose=embedding"
    ).json()["purpose"] == "embedding"
