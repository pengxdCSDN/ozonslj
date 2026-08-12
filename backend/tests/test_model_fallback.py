"""供应商降级和试运行开关测试。"""

import pytest

from backend.app.domain.model_budget import ModelBudgetPolicy, ModelBudgetUsage
from backend.app.domain.model_fallback import (
    BudgetAwareProviderRouter,
    ModelClient,
    ProviderCandidate,
    ProviderFallbackRouter,
    RolloutFlag,
    rollout_allows_execution,
)


class FakeClient(ModelClient):
    def __init__(self, value: str, fail: bool = False) -> None:
        self.value, self.fail = value, fail

    async def invoke(self, prompt: str) -> str:
        if self.fail:
            raise RuntimeError("quota")
        return self.value


@pytest.mark.asyncio
async def test_router_falls_back_after_provider_failure() -> None:
    router = ProviderFallbackRouter(
        {"deepseek": FakeClient("fail", True), "minimax": FakeClient("ok")},
        (ProviderCandidate("deepseek", "v3", 1), ProviderCandidate("minimax", "m1", 2)),
    )
    answer, provider = await router.invoke("hello")
    assert answer == "ok"
    assert provider.provider == "minimax"


def test_pilot_can_be_decided_by_admin_config() -> None:
    assert rollout_allows_execution(
        RolloutFlag("rag", "pilot", "2026-12-01"), is_admin=False, now_iso="2026-08-12"
    )
    assert not rollout_allows_execution(
        RolloutFlag("rag", "pilot", "2026-08-01"), is_admin=False, now_iso="2026-08-12"
    )


@pytest.mark.asyncio
async def test_budget_exceeded_provider_is_skipped_before_invoke() -> None:
    router = BudgetAwareProviderRouter(
        {"deepseek": FakeClient("blocked"), "minimax": FakeClient("ok")},
        (ProviderCandidate("deepseek", "v3", 1), ProviderCandidate("minimax", "m1", 2)),
        {
            "deepseek": (
                ModelBudgetPolicy("deepseek", 100, 100, 10, 100),
                ModelBudgetUsage(101, 0, 0, 0),
            )
        },
    )
    answer, provider = await router.invoke("hello")
    assert answer == "ok"
    assert provider.provider == "minimax"
