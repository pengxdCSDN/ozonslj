"""RAG 评测案例的 AI 草稿、人工确认和受控运行模型。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal, Protocol

EvaluationStatus = Literal["draft", "confirmed", "rejected"]


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """说明 EvaluationCase 的职责、状态边界和对外协作关系。"""
    case_id: str
    question: str
    expected_status: str
    expected_sources: tuple[str, ...]
    safety_tags: tuple[str, ...]
    status: EvaluationStatus = "draft"


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    """一次评测运行的脱敏汇总；指标由运行器完成后回写。"""
    run_id: str
    suite: str
    status: str
    gate_status: str
    target_count: int
    executed_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    metrics: dict[str, float | str] | None = None
    error_code: str | None = None


class RagEvaluationGateway(Protocol):
    """评测案例持久化端口；API 不直接依赖 PostgreSQL 驱动。"""

    async def seed_fixed_cases(self, cases: Sequence[EvaluationCase]) -> None:
        """执行 seed_fixed_cases 的业务流程并返回该流程的结果。

Args:
    cases: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def create_case(self, case: EvaluationCase) -> EvaluationCase:
        """执行 create_case 的业务流程并返回该流程的结果。

Args:
    case: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_cases(self) -> list[EvaluationCase]:
        """执行 list_cases 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""

    async def confirm_case(self, case_id: str, reviewer: str) -> EvaluationCase | None:
        """执行 confirm_case 的业务流程并返回该流程的结果。

Args:
    case_id: 参数语义、输入边界和安全约束。
    reviewer: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def confirm_cases(
        self, case_ids: Sequence[str], reviewer: str
    ) -> list[EvaluationCase]:
        """执行 confirm_cases 的业务流程并返回该流程的结果。

Args:
    case_ids: 参数语义、输入边界和安全约束。
    reviewer: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def create_run(self, suite: str, gate_status: Literal["ready", "blocked"]) -> str:
        """执行 create_run 的业务流程并返回该流程的结果。

Args:
    suite: 参数语义、输入边界和安全约束。
    gate_status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async def find_active_run(self, suite: str) -> EvaluationRun | None:
        """执行 find_active_run 的业务流程并返回该流程的结果。

Args:
    suite: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async def list_runs(self, limit: int = 20) -> list[EvaluationRun]:
        """执行 list_runs 的业务流程并返回该流程的结果。

Args:
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async def get_run(self, run_id: str) -> EvaluationRun | None:
        """执行 get_run 的业务流程并返回该流程的结果。

Args:
    run_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async def dispatchable_run_ids(self, limit: int) -> list[str]:
        """执行 dispatchable_run_ids 的业务流程并返回该流程的结果。

Args:
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async def claim_run(
        self, run_id: str, worker_id: str, lease_seconds: int
    ) -> EvaluationRun | None:
        """执行 claim_run 的业务流程并返回该流程的结果。

Args:
    run_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async def heartbeat_run(self, run_id: str, worker_id: str, lease_seconds: int) -> bool:
        """执行 heartbeat_run 的业务流程并返回该流程的结果。

Args:
    run_id: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    lease_seconds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async def save_run_metrics(
        self, run_id: str, metrics: dict[str, float | str], executed_count: int,
        passed_count: int, failed_count: int, error_count: int, worker_id: str | None = None,
        error_code: str | None = None,
    ) -> EvaluationRun | None:
        """执行 save_run_metrics 的业务流程并返回该流程的结果。

Args:
    run_id: 参数语义、输入边界和安全约束。
    metrics: 参数语义、输入边界和安全约束。
    executed_count: 参数语义、输入边界和安全约束。
    passed_count: 参数语义、输入边界和安全约束。
    failed_count: 参数语义、输入边界和安全约束。
    error_count: 参数语义、输入边界和安全约束。
    worker_id: 参数语义、输入边界和安全约束。
    error_code: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def confirm_case(case: EvaluationCase, *, reviewer: str) -> EvaluationCase:
    """执行 confirm_case 的业务流程并返回该流程的结果。

Args:
    case: 参数语义、输入边界和安全约束。
    reviewer: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if not reviewer.strip():
        raise ValueError("评测案例必须记录人工确认人")
    return replace(case, status="confirmed")


def suite_case_limit(suite: str) -> int:
    """执行 suite_case_limit 的业务流程并返回该流程的结果。

Args:
    suite: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    limits = {"quick": 30, "standard": 120, "full": 240}
    if suite not in limits:
        raise ValueError("suite 只能是 quick、standard 或 full")
    return limits[suite]
