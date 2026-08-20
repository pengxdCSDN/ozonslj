"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """说明 AuditEvent 的职责、状态边界和对外协作关系。"""
    event_type: str
    subject_id: str
    detail: dict[str, object]
    occurred_at: datetime


def create_audit_event(
    *,
    event_type: str,
    subject_id: str,
    detail: dict[str, object],
    occurred_at: datetime | None = None,
) -> AuditEvent:
    """执行 create_audit_event 的业务流程并返回该流程的结果。"""
    if not event_type.strip() or not subject_id.strip():
        raise ValueError("审计事件必须包含事件类型和对象标识")
    return AuditEvent(event_type, subject_id, detail, occurred_at or datetime.now(UTC))
