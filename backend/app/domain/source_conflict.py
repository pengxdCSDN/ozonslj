from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceConflict:
    field: str
    sources: list[str]
    values: list[str]
    message: str


def find_source_conflicts(
    records: dict[str, dict[str, object]], *, fields: list[str]
) -> list[SourceConflict]:
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
