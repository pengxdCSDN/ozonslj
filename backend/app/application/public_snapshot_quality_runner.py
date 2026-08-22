"""公开快照质量规则；异常进入隔离区，不修改公开样本事实。"""

from backend.app.domain.data_quality import QualityCheckJob, QualityFinding
from backend.app.domain.public_snapshot import PublicSnapshot, PublicSnapshotGateway


class PublicSnapshotQualityRunner:
    """读取工作区快照并检查来源、金额、评分和样本边界。"""

    def __init__(self, snapshots: PublicSnapshotGateway, *, page_size: int = 100) -> None:
        if not 1 <= page_size <= 500:
            raise ValueError("公开快照质量检查页大小必须在 1 到 500 之间")
        self._snapshots = snapshots
        self._page_size = page_size

    async def run(self, job: QualityCheckJob) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        snapshots = await self._snapshots.list_snapshots(
            workspace_id=job.workspace_id, limit=self._page_size
        )
        for snapshot in snapshots:
            findings.extend(_check_snapshot(snapshot))
        return _deduplicate(findings)


def _check_snapshot(snapshot: PublicSnapshot) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    if not snapshot.url.startswith("https://"):
        findings.append(QualityFinding(
            rule_code="PUB-001-HTTPS", field_name="url", severity="error",
            message="公开快照 URL 必须是 HTTPS",
        ))
    if snapshot.price_minor is not None and snapshot.price_minor < 0:
        findings.append(QualityFinding(
            rule_code="PUB-002-PRICE", field_name="price_minor", severity="error",
            message="公开快照价格不能为负数",
        ))
    if snapshot.rating is not None and not 0 <= snapshot.rating <= 5:
        findings.append(QualityFinding(
            rule_code="PUB-003-RATING", field_name="rating", severity="error",
            message="公开快照评分必须在 0 到 5 之间",
        ))
    if snapshot.sample_size < 1:
        findings.append(QualityFinding(
            rule_code="PUB-004-SAMPLE", field_name="sample_size", severity="error",
            message="公开快照样本数量必须为正数",
        ))
    if not snapshot.estimated:
        findings.append(QualityFinding(
            rule_code="PUB-005-SOURCE", field_name="estimated", severity="warning",
            message="公开样本必须标记为估算，不得冒充官方事实",
        ))
    return findings


def _deduplicate(findings: list[QualityFinding]) -> list[QualityFinding]:
    result: list[QualityFinding] = []
    seen: set[tuple[str, str, str]] = set()
    for finding in findings:
        key = (finding.rule_code, finding.field_name, finding.message)
        if key not in seen:
            seen.add(key)
            result.append(finding)
    return result
