from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class AuditEvent:
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
    if not event_type.strip() or not subject_id.strip():
        raise ValueError("审计事件必须包含事件类型和对象标识")
    return AuditEvent(event_type, subject_id, detail, occurred_at or datetime.now(UTC))
