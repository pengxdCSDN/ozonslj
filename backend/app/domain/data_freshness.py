from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DataFreshnessDecision:
    data_domain: str
    observed_at: datetime
    max_age_seconds: int
    age_seconds: int
    fresh: bool
    requires_refresh: bool
    message: str
    last_success_at: datetime | None = None
    window: str | None = None
    latency_seconds: int | None = None
    record_count: int | None = None
    error_summary: str | None = None


class DataFreshnessGateway(Protocol):
    async def save_decision(
        self, *, workspace_id: str, decision: DataFreshnessDecision
    ) -> DataFreshnessDecision: ...

    async def list_decisions(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[DataFreshnessDecision]: ...


def check_data_freshness(
    *, data_domain: str, observed_at: datetime, max_age_seconds: int,
    now: datetime | None = None,
    last_success_at: datetime | None = None,
    window: str | None = None,
    latency_seconds: int | None = None,
    record_count: int | None = None,
    error_summary: str | None = None,
) -> DataFreshnessDecision:
    if (
        not data_domain.strip()
        or isinstance(max_age_seconds, bool)
        or not isinstance(max_age_seconds, int)
        or max_age_seconds < 0
    ):
        raise ValueError("数据域和最大允许时效必须有效")
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    observed = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=UTC)
    if observed > reference:
        raise ValueError("数据观测时间不能晚于当前时间")
    if latency_seconds is not None and (isinstance(latency_seconds, bool) or latency_seconds < 0):
        raise ValueError("延迟必须是非负整数")
    if record_count is not None and (isinstance(record_count, bool) or record_count < 0):
        raise ValueError("记录数必须是非负整数")
    age = int((reference - observed).total_seconds())
    fresh = age <= max_age_seconds
    return DataFreshnessDecision(
        data_domain.strip(), observed, max_age_seconds, age, fresh, not fresh,
        "数据仍在允许时效内" if fresh else "数据已过期，必须重新读取并生成预览",
        last_success_at, window, latency_seconds, record_count, error_summary,
    )
