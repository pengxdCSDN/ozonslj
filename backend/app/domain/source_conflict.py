"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceConflict:
    """说明 SourceConflict 的职责、状态边界和对外协作关系。"""
    field: str
    sources: list[str]
    values: list[str]
    message: str


def find_source_conflicts(
    records: dict[str, dict[str, object]], *, fields: list[str]
) -> list[SourceConflict]:
    """执行 find_source_conflicts 的业务流程并返回该流程的结果。"""
    conflicts: list[SourceConflict] = []
    for field in fields:
        values = {source: data[field] for source, data in records.items() if field in data}
        unique = {str(value) for value in values.values()}
        if len(unique) > 1:
            conflicts.append(
                SourceConflict(
                    field,
                    list(values),
                    [str(value) for value in values.values()],
                    "不同来源事实不一致",
                )
            )
    return conflicts
