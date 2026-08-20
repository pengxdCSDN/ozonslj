"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol

from backend.app.domain.audit_event import AuditEvent


@dataclass(frozen=True, slots=True)
class StoredAuditEvent:
    """说明 StoredAuditEvent 的职责、状态边界和对外协作关系。"""
    event_id: str
    workspace_id: str
    event: AuditEvent


class AuditEventGateway(Protocol):
    """说明 AuditEventGateway 的职责、状态边界和对外协作关系。"""
    async def save(self, *, workspace_id: str, event: AuditEvent) -> StoredAuditEvent:
        """执行 save 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    event: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    async def list_events(self, *, workspace_id: str, limit: int) -> list[StoredAuditEvent]:
        """执行 list_events 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
