"""RAG 评测案例的 AI 草稿、人工确认和受控运行模型。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal, Protocol

EvaluationStatus = Literal["draft", "confirmed", "rejected"]


@dataclass(frozen=True, slots=True)
class EvaluationCase:
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


class RagEvaluationGateway(Protocol):
    """评测案例持久化端口；API 不直接依赖 PostgreSQL 驱动。"""

    async def seed_fixed_cases(self, cases: Sequence[EvaluationCase]) -> None: ...

    async def create_case(self, case: EvaluationCase) -> EvaluationCase: ...

    async def list_cases(self) -> list[EvaluationCase]: ...

    async def confirm_case(self, case_id: str, reviewer: str) -> EvaluationCase | None: ...

    async def confirm_cases(
        self, case_ids: Sequence[str], reviewer: str
    ) -> list[EvaluationCase]: ...

    async def create_run(self, suite: str, gate_status: Literal["ready", "blocked"]) -> str: ...
    async def find_active_run(self, suite: str) -> EvaluationRun | None: ...
    async def list_runs(self, limit: int = 20) -> list[EvaluationRun]: ...
    async def get_run(self, run_id: str) -> EvaluationRun | None: ...
    async def dispatchable_run_ids(self, limit: int) -> list[str]: ...
    async def claim_run(
        self, run_id: str, worker_id: str, lease_seconds: int
    ) -> EvaluationRun | None: ...
    async def heartbeat_run(self, run_id: str, worker_id: str, lease_seconds: int) -> bool: ...
    async def save_run_metrics(
        self, run_id: str, metrics: dict[str, float | str], executed_count: int,
        passed_count: int, failed_count: int, error_count: int, worker_id: str | None = None,
    ) -> EvaluationRun | None: ...


def confirm_case(case: EvaluationCase, *, reviewer: str) -> EvaluationCase:
    if not reviewer.strip():
        raise ValueError("评测案例必须记录人工确认人")
    return replace(case, status="confirmed")


def suite_case_limit(suite: str) -> int:
    limits = {"quick": 30, "standard": 120, "full": 240}
    if suite not in limits:
        raise ValueError("suite 只能是 quick、standard 或 full")
    return limits[suite]
