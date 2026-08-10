from datetime import UTC, datetime

import pytest

from backend.app.domain.audit_event import create_audit_event


def test_audit_event_preserves_stage_and_time() -> None:
    occurred = datetime(2026, 8, 9, tzinfo=UTC)
    event = create_audit_event(
        event_type="approved",
        subject_id="cmd-1",
        detail={"reviewer": "运营人员"},
        occurred_at=occurred,
    )
    assert event.event_type == "approved"
    assert event.occurred_at == occurred


def test_audit_event_requires_identity() -> None:
    with pytest.raises(ValueError):
        create_audit_event(event_type="", subject_id="cmd-1", detail={})
