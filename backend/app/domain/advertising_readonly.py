from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingReadOnlyDecision:
    action: str
    allowed: bool
    reason: str
    audit_required: bool


class AdvertisingBoundaryGateway(Protocol):
    async def save_check(
        self, *, workspace_id: str, decision: AdvertisingReadOnlyDecision
    ) -> AdvertisingReadOnlyDecision: ...

    async def list_checks(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingReadOnlyDecision]: ...


READ_ONLY_ACTIONS = frozenset({"diagnose", "build_calendar", "calculate_metrics", "read_report"})
WRITE_ACTIONS = frozenset({"change_budget", "change_bid", "change_negative_keyword"})


def check_advertising_action(action: str) -> AdvertisingReadOnlyDecision:
    normalized = action.strip().lower()
    if normalized in READ_ONLY_ACTIONS:
        return AdvertisingReadOnlyDecision(normalized, True, "广告功能仅生成只读分析结果", False)
    if normalized in WRITE_ACTIONS:
        return AdvertisingReadOnlyDecision(
            normalized, False, "广告建议不得自动修改预算、出价或否定词", True
        )
    return AdvertisingReadOnlyDecision(normalized, False, "未注册的广告动作默认拒绝", True)
