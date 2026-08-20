"""说明本模块的职责、边界和主要协作对象。"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SampleScope:
    """说明 SampleScope 的职责、状态边界和对外协作关系。"""
    sample_count: int
    sampled_from: datetime | None
    sampled_to: datetime | None
    estimated: bool
    missing_fields: tuple[str, ...]
    caveat: str


def summarize_sample_scope(records: Sequence[dict[str, object]]) -> SampleScope:
    """生成必须随公开样本结论展示的范围和不确定性摘要。"""
    times = [value for record in records if isinstance(value := record.get("sampled_at"), datetime)]
    missing: set[str] = set()
    tracked_fields = ("title", "price_minor", "rating", "review_count", "image_url")
    for record in records:
        missing.update(field for field in tracked_fields if record.get(field) in (None, ""))
    return SampleScope(
        sample_count=len(records),
        sampled_from=min(times) if times else None,
        sampled_to=max(times) if times else None,
        estimated=True,
        missing_fields=tuple(sorted(missing)),
        caveat="公开样本仅用于趋势和竞品辅助判断，不代表全市场精确事实",
    )
