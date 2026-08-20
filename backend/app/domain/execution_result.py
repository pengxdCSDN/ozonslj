"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ItemExecutionResult:
    """说明 ItemExecutionResult 的职责、状态边界和对外协作关系。"""
    item_id: str
    success: bool
    message: str


@dataclass(frozen=True, slots=True)
class BatchExecutionResult:
    """说明 BatchExecutionResult 的职责、状态边界和对外协作关系。"""
    total: int
    succeeded: int
    failed: int
    status: str
    items: list[ItemExecutionResult]


def summarize_execution(items: list[ItemExecutionResult]) -> BatchExecutionResult:
    """执行 summarize_execution 的业务流程并返回该流程的结果。"""
    succeeded = sum(item.success for item in items)
    failed = len(items) - succeeded
    status = "success" if failed == 0 and items else "partial_failure" if succeeded else "failure"
    return BatchExecutionResult(len(items), succeeded, failed, status, items)
