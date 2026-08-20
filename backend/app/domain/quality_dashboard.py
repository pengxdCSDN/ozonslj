"""说明本模块的职责、边界和主要协作对象。"""

from collections import Counter
from dataclasses import dataclass

from backend.app.domain.data_quality import QualityFindingRecord


@dataclass(frozen=True, slots=True)
class QualityDashboardSummary:
    """说明 QualityDashboardSummary 的职责、状态边界和对外协作关系。"""
    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_rule: dict[str, int]


def summarize_quality_findings(findings: list[QualityFindingRecord]) -> QualityDashboardSummary:
    """执行 summarize_quality_findings 的业务流程并返回该流程的结果。

Args:
    findings: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return QualityDashboardSummary(
        total=len(findings),
        by_severity=dict(Counter(item.severity for item in findings)),
        by_status=dict(Counter(item.status for item in findings)),
        by_rule=dict(Counter(item.rule_code for item in findings)),
    )
