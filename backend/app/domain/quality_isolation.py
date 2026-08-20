"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IsolatedRecord:
    """说明 IsolatedRecord 的职责、状态边界和对外协作关系。"""
    row_index: int
    reason: str
    record: dict[str, object]


@dataclass(frozen=True, slots=True)
class IsolationResult:
    """说明 IsolationResult 的职责、状态边界和对外协作关系。"""
    accepted: list[dict[str, object]]
    isolated: list[IsolatedRecord]


def isolate_invalid_records(
    records: list[dict[str, object]], invalid_rows: set[int], *, reason: str
) -> IsolationResult:
    """执行 isolate_invalid_records 的业务流程并返回该流程的结果。

Args:
    records: 参数语义、输入边界和安全约束。
    invalid_rows: 参数语义、输入边界和安全约束。
    reason: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
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
