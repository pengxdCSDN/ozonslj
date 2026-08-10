from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from backend.app.domain.execution_result import BatchExecutionResult


@dataclass(frozen=True, slots=True)
class StoredExecutionResult:
    """批量执行结果的持久化记录；只保存脱敏后的逐项状态和用户可见消息。"""

    result_id: str
    workspace_id: str
    result: BatchExecutionResult
    created_at: datetime


class ExecutionResultGateway(Protocol):
    async def save(
        self, *, workspace_id: str, result: BatchExecutionResult
    ) -> StoredExecutionResult: ...

    async def list_results(
        self, *, workspace_id: str, limit: int
    ) -> list[StoredExecutionResult]: ...
