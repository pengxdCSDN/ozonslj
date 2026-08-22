"""数据质量检查 Worker；只消费质量任务，不触发外部写操作。"""

from typing import Protocol

from backend.app.domain.data_quality import (
    QualityCheckJob,
    QualityCheckJobGateway,
    QualityFinding,
    QualityFindingGateway,
)


class QualityRuleRunner(Protocol):
    """质量规则执行端口；规则只能读取事实并返回脱敏问题。"""

    async def run(self, job: QualityCheckJob) -> list[QualityFinding]:
        """执行规则并返回质量问题。"""


class QualityTaskConsumer(Protocol):
    """质量任务消息确认端口。"""

    async def read_one(self, *, block_ms: int) -> tuple[str, str] | None:
        """读取消息 ID 和质量任务 ID。"""

    async def acknowledge(self, message_id: str) -> None:
        """确认已处理消息。"""


class QualityCheckWorker:
    """领取质量任务、写入 findings 并安全确认消息。"""

    def __init__(
        self,
        jobs: QualityCheckJobGateway,
        findings: QualityFindingGateway,
        consumer: QualityTaskConsumer,
        runner: QualityRuleRunner,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        retry_delay_seconds: int = 60,
    ) -> None:
        self._jobs = jobs
        self._findings = findings
        self._consumer = consumer
        self._runner = runner
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._retry_delay_seconds = retry_delay_seconds

    async def process_one(self, *, block_ms: int = 1_000) -> bool:
        """处理一条质量任务；成功落库后才确认 Redis 消息。"""
        message = await self._consumer.read_one(block_ms=block_ms)
        if message is None:
            return False
        message_id, job_id = message
        job = await self._jobs.claim_quality_check(
            job_id=job_id, worker_id=self._worker_id, lease_seconds=self._lease_seconds
        )
        if job is None:
            await self._consumer.acknowledge(message_id)
            return True
        try:
            findings = await self._runner.run(job)
            if findings:
                await self._findings.create_findings(
                    workspace_id=job.workspace_id, findings=findings
                )
            persisted = await self._jobs.complete_quality_check(
                job_id=job.id, worker_id=self._worker_id
            )
        except Exception:
            persisted = await self._jobs.fail_quality_check(
                job_id=job.id, worker_id=self._worker_id,
                retry_delay_seconds=self._retry_delay_seconds,
            )
        if persisted:
            await self._consumer.acknowledge(message_id)
        return persisted
