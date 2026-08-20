"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from backend.app.domain.readback_verification import ReadbackVerification


@dataclass(frozen=True, slots=True)
class StoredReadbackVerification:
    """工作区范围的回读证据，保留差异而不覆盖历史结果。"""

    verification_id: str
    workspace_id: str
    verification: ReadbackVerification
    created_at: datetime


class ReadbackVerificationGateway(Protocol):
    """说明 ReadbackVerificationGateway 的职责、状态边界和对外协作关系。"""
    async def save(
        self, *, workspace_id: str, verification: ReadbackVerification
    ) -> StoredReadbackVerification:
        """执行 save 的业务流程并返回该流程的结果。"""

    async def list_results(
        self, *, workspace_id: str, limit: int
    ) -> list[StoredReadbackVerification]:
        """执行 list_results 的业务流程并返回该流程的结果。"""
