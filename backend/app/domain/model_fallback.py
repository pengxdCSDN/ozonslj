"""模型供应商路由、配额降级和试运行开关。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from backend.app.domain.model_budget import ModelBudgetPolicy, ModelBudgetUsage, decide_budget

ProviderStatus = Literal["available", "quota_exceeded", "timeout", "unavailable", "disabled"]
RolloutMode = Literal["disabled", "shadow", "pilot", "internal"]


@dataclass(frozen=True, slots=True)
class ProviderCandidate:
    """说明 ProviderCandidate 的职责、状态边界和对外协作关系。"""
    provider: str
    model: str
    priority: int
    status: ProviderStatus = "available"


@dataclass(frozen=True, slots=True)
class RolloutFlag:
    """说明 RolloutFlag 的职责、状态边界和对外协作关系。"""
    name: str
    mode: RolloutMode
    pilot_until: str | None = None


class ModelClient(Protocol):
    """说明 ModelClient 的职责、状态边界和对外协作关系。"""
    async def invoke(self, prompt: str) -> str:
        """执行 invoke 的业务流程并返回该流程的结果。

Args:
    prompt: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class ProviderFallbackRouter:
    """按优先级选择可用供应商；过量、超时和不可用都会自动降级。"""

    def __init__(
        self, clients: dict[str, ModelClient], candidates: tuple[ProviderCandidate, ...]
    ) -> None:
        """初始化对象依赖和运行时状态。

Args:
    clients: 参数语义、输入边界和安全约束。
    candidates: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._clients = clients
        self._candidates = candidates

    async def invoke(self, prompt: str) -> tuple[str, ProviderCandidate]:
        """执行 invoke 的业务流程并返回该流程的结果。

Args:
    prompt: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
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
        """初始化对象依赖和运行时状态。

Args:
    clients: 参数语义、输入边界和安全约束。
    candidates: 参数语义、输入边界和安全约束。
    budgets: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        super().__init__(clients, candidates)
        self._budget_candidates = candidates
        self._budgets = budgets

    async def invoke(self, prompt: str) -> tuple[str, ProviderCandidate]:
        """执行 invoke 的业务流程并返回该流程的结果。

Args:
    prompt: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
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
    """执行内部步骤 _budget_allows，供同一模块的公开流程复用。

Args:
    candidate: 参数语义、输入边界和安全约束。
    budgets: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    configured = budgets.get(candidate.provider)
    if configured is None:
        return True
    policy, usage = configured
    return decide_budget(policy, usage).allowed


def rollout_allows_execution(flag: RolloutFlag, *, is_admin: bool, now_iso: str) -> bool:
    """统一判断试运行模式；pilot 到期或 disabled 不执行。

Args:
    flag: 参数语义、输入边界和安全约束。
    is_admin: 参数语义、输入边界和安全约束。
    now_iso: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    if flag.mode == "disabled":
        return False
    if flag.mode == "internal" and not is_admin:
        return False
    expired = flag.mode == "pilot" and flag.pilot_until is not None and now_iso >= flag.pilot_until
    return not expired
