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


def confirm_case(case: EvaluationCase, *, reviewer: str) -> EvaluationCase:
    if not reviewer.strip():
        raise ValueError("评测案例必须记录人工确认人")
    return replace(case, status="confirmed")


def suite_case_limit(suite: str) -> int:
    limits = {"quick": 30, "standard": 120, "full": 240}
    if suite not in limits:
        raise ValueError("suite 只能是 quick、standard 或 full")
    return limits[suite]
