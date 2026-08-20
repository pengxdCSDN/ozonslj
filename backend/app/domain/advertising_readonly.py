"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingReadOnlyDecision:
    """说明 AdvertisingReadOnlyDecision 的职责、状态边界和对外协作关系。"""
    action: str
    allowed: bool
    reason: str
    audit_required: bool


class AdvertisingBoundaryGateway(Protocol):
    """说明 AdvertisingBoundaryGateway 的职责、状态边界和对外协作关系。"""
    async def save_check(
        self, *, workspace_id: str, decision: AdvertisingReadOnlyDecision
    ) -> AdvertisingReadOnlyDecision:
        """执行 save_check 的业务流程并返回该流程的结果。"""

    async def list_checks(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingReadOnlyDecision]:
        """执行 list_checks 的业务流程并返回该流程的结果。"""


READ_ONLY_ACTIONS = frozenset({"diagnose", "build_calendar", "calculate_metrics", "read_report"})
WRITE_ACTIONS = frozenset({"change_budget", "change_bid", "change_negative_keyword"})


def check_advertising_action(action: str) -> AdvertisingReadOnlyDecision:
    """执行 check_advertising_action 的业务流程并返回该流程的结果。"""
    normalized = action.strip().lower()
    if normalized in READ_ONLY_ACTIONS:
        return AdvertisingReadOnlyDecision(normalized, True, "广告功能仅生成只读分析结果", False)
    if normalized in WRITE_ACTIONS:
        return AdvertisingReadOnlyDecision(
            normalized, False, "广告建议不得自动修改预算、出价或否定词", True
        )
    return AdvertisingReadOnlyDecision(normalized, False, "未注册的广告动作默认拒绝", True)
