"""质量检查 Worker 的领取、写入、确认和失败重试测试。"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from backend.app.application.quality_check_worker import QualityCheckWorker
from backend.app.domain.data_quality import QualityCheckJob, QualityFinding


def _job() -> QualityCheckJob:
    return QualityCheckJob(
        id="quality-1", workspace_id="workspace-1", status="running", data_version="v1",
        idempotency_key="key-1", parent_run_id="run-1", attempt_count=1,
        created_at=datetime.now(UTC),
    )


@dataclass
class FakeConsumer:
    acknowledged: list[str] = field(default_factory=list)

    async def read_one(self, *, block_ms: int) -> tuple[str, str]:
        del block_ms
        return ("1-0", "quality-1")

    async def acknowledge(self, message_id: str) -> None:
        self.acknowledged.append(message_id)


@dataclass
class FakeJobs:
    claimed: QualityCheckJob | None = field(default_factory=_job)
    completed: bool = True
    failed: bool = True

    async def claim_quality_check(self, **kwargs: object) -> QualityCheckJob | None:
        del kwargs
        return self.claimed

    async def complete_quality_check(self, **kwargs: object) -> bool:
        del kwargs
        return self.completed

    async def fail_quality_check(self, **kwargs: object) -> bool:
        del kwargs
        return self.failed


@dataclass
class FakeFindings:
    created: list[QualityFinding] = field(default_factory=list)

    async def create_findings(
        self, *, workspace_id: str, findings: list[QualityFinding]
    ) -> list[object]:
        del workspace_id
        self.created.extend(findings)
        return []


class Runner:
    async def run(self, job: QualityCheckJob) -> list[QualityFinding]:
        del job
        return [QualityFinding(
            rule_code="DQ-TEST", field_name="price", severity="error", message="测试问题"
        )]


class FailingRunner:
    async def run(self, job: QualityCheckJob) -> list[QualityFinding]:
        del job
        raise RuntimeError("rule failed")


def test_worker_writes_findings_before_acknowledging() -> None:
    consumer, jobs, findings = FakeConsumer(), FakeJobs(), FakeFindings()
    worker = QualityCheckWorker(jobs, findings, consumer, Runner(), worker_id="quality-1")

    assert asyncio.run(worker.process_one()) is True
    assert len(findings.created) == 1
    assert consumer.acknowledged == ["1-0"]


def test_worker_routes_rule_failure_to_retry_and_acknowledges() -> None:
    consumer, jobs, findings = FakeConsumer(), FakeJobs(), FakeFindings()
    worker = QualityCheckWorker(jobs, findings, consumer, FailingRunner(), worker_id="quality-1")

    assert asyncio.run(worker.process_one()) is True
    assert findings.created == []
    assert consumer.acknowledged == ["1-0"]
