"""RAG 评测案例的 AI 草稿、人工确认和受控运行模型。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

EvaluationStatus = Literal["draft", "confirmed", "rejected"]


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    question: str
    expected_status: str
    expected_sources: tuple[str, ...]
    safety_tags: tuple[str, ...]
    status: EvaluationStatus = "draft"


def confirm_case(case: EvaluationCase, *, reviewer: str) -> EvaluationCase:
    if not reviewer.strip():
        raise ValueError("评测案例必须记录人工确认人")
    return replace(case, status="confirmed")


def suite_case_limit(suite: str) -> int:
    limits = {"quick": 30, "standard": 120, "full": 240}
    if suite not in limits:
        raise ValueError("suite 只能是 quick、standard 或 full")
    return limits[suite]
