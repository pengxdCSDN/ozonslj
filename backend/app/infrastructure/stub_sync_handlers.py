from backend.app.domain.sync_job import SyncJob, SyncResult


class StubSyncHandler:
    """开发与自动化测试使用的确定性只读同步处理器。"""

    def __init__(self, *, processed_count: int = 0) -> None:
        self._processed_count = processed_count

    async def run(self, job: SyncJob) -> SyncResult:
        del job
        return SyncResult(processed_count=self._processed_count, failure_count=0)
