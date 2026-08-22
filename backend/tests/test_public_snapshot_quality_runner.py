import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from backend.app.application.public_snapshot_quality_runner import PublicSnapshotQualityRunner
from backend.app.domain.data_quality import QualityCheckJob
from backend.app.domain.public_snapshot import PublicSnapshot


class StubSnapshots:
    def __init__(self, items: list[PublicSnapshot]) -> None:
        self.items = items

    async def list_snapshots(self, *, workspace_id: str, limit: int = 50) -> list[PublicSnapshot]:
        del workspace_id
        return self.items[:limit]

    async def save_snapshot(self, *, workspace_id: str, snapshot: PublicSnapshot) -> PublicSnapshot:
        del workspace_id
        return snapshot


def test_public_snapshot_quality_runner_reports_source_boundary() -> None:
    snapshot = PublicSnapshot(
        url="http://example.com/item",
        sampled_at=datetime.now(UTC),
        title="Item",
        price_minor=100,
        currency="RUB",
        rating=Decimal("4.5"),
        review_count=1,
        image_url=None,
        attributes={},
        sample_size=1,
        estimated=False,
    )
    job = QualityCheckJob(
        id="job-1", workspace_id="store-1", status="queued", data_version="v1",
        idempotency_key="key-1", parent_run_id="run-1", attempt_count=0,
        created_at=datetime.now(UTC),
    )

    findings = asyncio.run(PublicSnapshotQualityRunner(StubSnapshots([snapshot])).run(job))

    assert {finding.rule_code for finding in findings} == {"PUB-001-HTTPS", "PUB-005-SOURCE"}
