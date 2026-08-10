from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingThresholds:
    version: int
    min_impressions: int
    min_clicks: int
    high_cvr_percent: float
    high_spend_minor: int


class AdvertisingThresholdGateway(Protocol):
    async def save(
        self, *, workspace_id: str, thresholds: AdvertisingThresholds
    ) -> AdvertisingThresholds: ...

    async def list_versions(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingThresholds]: ...


def create_advertising_thresholds(
    *, version: int, min_impressions: int, min_clicks: int,
    high_cvr_percent: float, high_spend_minor: int,
) -> AdvertisingThresholds:
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
