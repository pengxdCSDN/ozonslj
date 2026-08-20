"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingThresholds:
    """说明 AdvertisingThresholds 的职责、状态边界和对外协作关系。"""
    version: int
    min_impressions: int
    min_clicks: int
    high_cvr_percent: float
    high_spend_minor: int


class AdvertisingThresholdGateway(Protocol):
    """说明 AdvertisingThresholdGateway 的职责、状态边界和对外协作关系。"""
    async def save(
        self, *, workspace_id: str, thresholds: AdvertisingThresholds
    ) -> AdvertisingThresholds:
        """执行 save 的业务流程并返回该流程的结果。"""

    async def list_versions(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingThresholds]:
        """执行 list_versions 的业务流程并返回该流程的结果。"""


def create_advertising_thresholds(
    *, version: int, min_impressions: int, min_clicks: int,
    high_cvr_percent: float, high_spend_minor: int,
) -> AdvertisingThresholds:
    """执行 create_advertising_thresholds 的业务流程并返回该流程的结果。"""
    integer_values = (version, min_impressions, min_clicks, high_spend_minor)
    if (
        any(isinstance(value, bool) or not isinstance(value, int) for value in integer_values)
        or version < 1 or min_impressions < 0 or min_clicks < 0
        or high_cvr_percent < 0 or high_spend_minor < 0
    ):
        raise ValueError("广告阈值必须是非负值，版本必须从 1 开始")
    return AdvertisingThresholds(
        version, min_impressions, min_clicks, high_cvr_percent, high_spend_minor
    )
