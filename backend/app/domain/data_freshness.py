"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DataFreshnessDecision:
    """说明 DataFreshnessDecision 的职责、状态边界和对外协作关系。"""
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
    """说明 DataFreshnessGateway 的职责、状态边界和对外协作关系。"""
    async def save_decision(
        self, *, workspace_id: str, decision: DataFreshnessDecision
    ) -> DataFreshnessDecision:
        """执行 save_decision 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_decisions(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[DataFreshnessDecision]:
        """执行 list_decisions 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def check_data_freshness(
    *, data_domain: str, observed_at: datetime, max_age_seconds: int,
    now: datetime | None = None,
    last_success_at: datetime | None = None,
    window: str | None = None,
    latency_seconds: int | None = None,
    record_count: int | None = None,
    error_summary: str | None = None,
) -> DataFreshnessDecision:
    """执行 check_data_freshness 的业务流程并返回该流程的结果。

Args:
    data_domain: 参数语义、输入边界和安全约束。
    observed_at: 参数语义、输入边界和安全约束。
    max_age_seconds: 参数语义、输入边界和安全约束。
    now: 参数语义、输入边界和安全约束。
    last_success_at: 参数语义、输入边界和安全约束。
    window: 参数语义、输入边界和安全约束。
    latency_seconds: 参数语义、输入边界和安全约束。
    record_count: 参数语义、输入边界和安全约束。
    error_summary: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
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
