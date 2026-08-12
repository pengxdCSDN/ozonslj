"""模型供应商路由、配额降级和试运行开关。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from backend.app.domain.model_budget import ModelBudgetPolicy, ModelBudgetUsage, decide_budget

ProviderStatus = Literal["available", "quota_exceeded", "timeout", "unavailable", "disabled"]
RolloutMode = Literal["disabled", "shadow", "pilot", "internal"]


@dataclass(frozen=True, slots=True)
class ProviderCandidate:
    provider: str
    model: str
    priority: int
    status: ProviderStatus = "available"


@dataclass(frozen=True, slots=True)
class RolloutFlag:
    name: str
    mode: RolloutMode
    pilot_until: str | None = None


class ModelClient(Protocol):
    async def invoke(self, prompt: str) -> str: ...


class ProviderFallbackRouter:
    """按优先级选择可用供应商；过量、超时和不可用都会自动降级。"""

    def __init__(
        self, clients: dict[str, ModelClient], candidates: tuple[ProviderCandidate, ...]
    ) -> None:
        self._clients = clients
        self._candidates = candidates

    async def invoke(self, prompt: str) -> tuple[str, ProviderCandidate]:
        errors: list[str] = []
        for candidate in sorted(self._candidates, key=lambda item: item.priority):
            if candidate.status != "available" or candidate.provider not in self._clients:
                continue
            try:
                return await self._clients[candidate.provider].invoke(prompt), candidate
            except (TimeoutError, RuntimeError) as error:
                errors.append(f"{candidate.provider}:{type(error).__name__}")
        raise RuntimeError("所有模型供应商均不可用，已安全降级；" + ",".join(errors))


class BudgetAwareProviderRouter(ProviderFallbackRouter):
    """调用前执行额度门禁，再复用主备异常降级逻辑。"""

    def __init__(
        self,
        clients: dict[str, ModelClient],
        candidates: tuple[ProviderCandidate, ...],
        budgets: dict[str, tuple[ModelBudgetPolicy, ModelBudgetUsage]],
    ) -> None:
        super().__init__(clients, candidates)
        self._budget_candidates = candidates
        self._budgets = budgets

    async def invoke(self, prompt: str) -> tuple[str, ProviderCandidate]:
        eligible = tuple(
            candidate
            for candidate in self._budget_candidates
            if _budget_allows(candidate, self._budgets)
        )
        if not eligible:
            raise RuntimeError("所有模型供应商额度均已超限，无法调用")
        return await ProviderFallbackRouter(self._clients, eligible).invoke(prompt)


def _budget_allows(
    candidate: ProviderCandidate,
    budgets: dict[str, tuple[ModelBudgetPolicy, ModelBudgetUsage]],
) -> bool:
    configured = budgets.get(candidate.provider)
    if configured is None:
        return True
    policy, usage = configured
    return decide_budget(policy, usage).allowed


def rollout_allows_execution(flag: RolloutFlag, *, is_admin: bool, now_iso: str) -> bool:
    """统一判断试运行模式；pilot 到期或 disabled 不执行。"""

    if flag.mode == "disabled":
        return False
    if flag.mode == "internal" and not is_admin:
        return False
    expired = flag.mode == "pilot" and flag.pilot_until is not None and now_iso >= flag.pilot_until
    return not expired
