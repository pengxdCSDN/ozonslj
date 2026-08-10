from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IsolatedRecord:
    row_index: int
    reason: str
    record: dict[str, object]


@dataclass(frozen=True, slots=True)
class IsolationResult:
    accepted: list[dict[str, object]]
    isolated: list[IsolatedRecord]


def isolate_invalid_records(
    records: list[dict[str, object]], invalid_rows: set[int], *, reason: str
) -> IsolationResult:
    if not reason.strip():
        raise ValueError("隔离原因不能为空")
    accepted = [
        record for index, record in enumerate(records, start=1) if index not in invalid_rows
    ]
    isolated = [
        IsolatedRecord(index, reason, records[index - 1])
        for index in sorted(invalid_rows)
        if 1 <= index <= len(records)
    ]
    return IsolationResult(accepted, isolated)
