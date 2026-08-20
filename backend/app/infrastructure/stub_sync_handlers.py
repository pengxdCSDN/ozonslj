"""说明本模块的职责、边界和主要协作对象。"""

from backend.app.domain.sync_job import SyncJob, SyncResult


class StubSyncHandler:
    """开发与自动化测试使用的确定性只读同步处理器。"""

    def __init__(self, *, processed_count: int = 0) -> None:
        """初始化对象依赖和运行时状态。"""
        self._processed_count = processed_count

    async def run(self, job: SyncJob) -> SyncResult:
        """执行 run 的业务流程并返回该流程的结果。"""
        del job
        return SyncResult(processed_count=self._processed_count, failure_count=0)
