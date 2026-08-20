"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from backend.app.domain.data_freshness import check_data_freshness


@dataclass(frozen=True, slots=True)
class DiffPreview:
    """说明 DiffPreview 的职责、状态边界和对外协作关系。"""
    field: str
    old_value: str | None
    new_value: str | None
    source: str
    impact: str
    requires_review: bool


class StalePreviewError(ValueError):
    """差异预览引用的数据已过期，必须重新读取后再生成预览。"""


class DiffPreviewGateway(Protocol):
    """说明 DiffPreviewGateway 的职责、状态边界和对外协作关系。"""
    async def save_preview(
        self, *, workspace_id: str, previews: list[DiffPreview]
    ) -> list[DiffPreview]:
        """执行 save_preview 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    previews: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def build_diff_preview(
    *, old_values: dict[str, object], new_values: dict[str, object],
    source: str, impact: str,
    observed_at: datetime | None = None,
    max_age_seconds: int | None = None,
    now: datetime | None = None,
) -> list[DiffPreview]:
    """执行 build_diff_preview 的业务流程并返回该流程的结果。

Args:
    old_values: 参数语义、输入边界和安全约束。
    new_values: 参数语义、输入边界和安全约束。
    source: 参数语义、输入边界和安全约束。
    impact: 参数语义、输入边界和安全约束。
    observed_at: 参数语义、输入边界和安全约束。
    max_age_seconds: 参数语义、输入边界和安全约束。
    now: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
    StalePreviewError: 业务约束或外部依赖失败时抛出。
"""
    if not source.strip() or not impact.strip():
        raise ValueError("差异预览必须包含来源和影响说明")
    # 只要提供新鲜度元数据，就把它作为预览硬门槛，避免过期状态进入审核链路。
    if (observed_at is None) != (max_age_seconds is None):
        raise ValueError("预览的新鲜度必须同时提供观测时间和最大允许时效")
    if observed_at is not None and max_age_seconds is not None:
        freshness = check_data_freshness(
            data_domain="review_diff_preview",
            observed_at=observed_at,
            max_age_seconds=max_age_seconds,
            now=now,
        )
        if freshness.requires_refresh:
            raise StalePreviewError(freshness.message)
    fields = list(dict.fromkeys([*old_values, *new_values]))
    return [
        DiffPreview(
            field=field,
            old_value=None if old_values.get(field) is None else str(old_values.get(field)),
            new_value=None if new_values.get(field) is None else str(new_values.get(field)),
            source=source.strip(), impact=impact.strip(), requires_review=True,
        )
        for field in fields
        if old_values.get(field) != new_values.get(field)
    ]
