"""说明本模块的职责、边界和主要协作对象。"""

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
    """说明 ExecutionResultGateway 的职责、状态边界和对外协作关系。"""
    async def save(
        self, *, workspace_id: str, result: BatchExecutionResult
    ) -> StoredExecutionResult:
        """执行 save 的业务流程并返回该流程的结果。"""

    async def list_results(
        self, *, workspace_id: str, limit: int
    ) -> list[StoredExecutionResult]:
        """执行 list_results 的业务流程并返回该流程的结果。"""
