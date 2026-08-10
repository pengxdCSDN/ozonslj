from dataclasses import dataclass
from typing import Protocol

from backend.app.domain.audit_event import AuditEvent


@dataclass(frozen=True, slots=True)
class StoredAuditEvent:
    event_id: str
    workspace_id: str
    event: AuditEvent


class AuditEventGateway(Protocol):
    async def save(self, *, workspace_id: str, event: AuditEvent) -> StoredAuditEvent: ...
    async def list_events(self, *, workspace_id: str, limit: int) -> list[StoredAuditEvent]: ...
