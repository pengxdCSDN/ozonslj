from datetime import UTC, datetime

from backend.app.domain.relationship_quality import check_relationship_and_time


def test_relationship_quality_finds_orphan_duplicate_and_time_backward() -> None:
    findings = check_relationship_and_time(
        [
            {"id": "1", "parent_id": "p", "observed_at": datetime(2026, 8, 2, tzinfo=UTC)},
            {"id": "1", "parent_id": "missing", "observed_at": datetime(2026, 8, 1, tzinfo=UTC)},
        ],
        parent_ids={"p"},
    )
    assert {finding.rule_code for finding in findings} == {
        "DQ-004-DUPLICATE", "DQ-004-ORPHAN", "DQ-004-TIME-BACKWARD"
    }
