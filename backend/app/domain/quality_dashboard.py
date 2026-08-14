from collections import Counter
from dataclasses import dataclass

from backend.app.domain.data_quality import QualityFindingRecord


@dataclass(frozen=True, slots=True)
class QualityDashboardSummary:
    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_rule: dict[str, int]


def summarize_quality_findings(findings: list[QualityFindingRecord]) -> QualityDashboardSummary:
    return QualityDashboardSummary(
        total=len(findings),
        by_severity=dict(Counter(item.severity for item in findings)),
        by_status=dict(Counter(item.status for item in findings)),
        by_rule=dict(Counter(item.rule_code for item in findings)),
    )
