from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ItemExecutionResult:
    item_id: str
    success: bool
    message: str


@dataclass(frozen=True, slots=True)
class BatchExecutionResult:
    total: int
    succeeded: int
    failed: int
    status: str
    items: list[ItemExecutionResult]


def summarize_execution(items: list[ItemExecutionResult]) -> BatchExecutionResult:
    succeeded = sum(item.success for item in items)
    failed = len(items) - succeeded
    status = "success" if failed == 0 and items else "partial_failure" if succeeded else "failure"
    return BatchExecutionResult(len(items), succeeded, failed, status, items)
