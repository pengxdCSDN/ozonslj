from datetime import UTC, datetime

from backend.app.domain.data_quality import QualityFindingRecord
from backend.app.domain.quality_dashboard import summarize_quality_findings


def test_quality_dashboard_groups_open_findings() -> None:
    finding = QualityFindingRecord(
        id="1", workspace_id="w", rule_code="DQ-005", field_name="price",
        severity="error", message="金额异常", created_at=datetime.now(UTC),
    )
    summary = summarize_quality_findings([finding])
    assert summary.total == 1
    assert summary.by_rule == {"DQ-005": 1}
