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
    async def save(
        self, *, workspace_id: str, verification: ReadbackVerification
    ) -> StoredReadbackVerification: ...

    async def list_results(
        self, *, workspace_id: str, limit: int
    ) -> list[StoredReadbackVerification]: ...
