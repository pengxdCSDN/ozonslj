import asyncio
from dataclasses import dataclass
from typing import Protocol

from backend.app.domain.sync_job import SyncJob, SyncResult


@dataclass(frozen=True, slots=True)
class SyncPage:
    """上游分页响应的内部模型，隔离 Ozon 传输字段。"""

    items: tuple[object, ...]
    next_cursor: str | None


class RetryableSyncError(RuntimeError):
    """上游限流或临时不可用错误，可按 Retry-After 重试。"""

    def __init__(self, message: str = "上游暂时不可用", retry_after_seconds: float = 0.0) -> None:
        super().__init__(message)
        self.retry_after_seconds = max(retry_after_seconds, 0.0)


class SyncPageFetcher(Protocol):
    async def fetch_page(
        self, *, workspace_id: str, resource_type: str, cursor: str | None
    ) -> SyncPage: ...


class SyncPageSink(Protocol):
    """将已成功读取的页面映射并保存为 PostgreSQL 事实。"""

    async def save_page(self, *, job: SyncJob, page: SyncPage) -> None: ...


class SyncWatermarkStore(Protocol):
    """仅在完整同步成功后保存长期水位，避免失败任务推进水位。"""

    async def advance(self, *, job: SyncJob, cursor: str | None) -> None: ...


class PaginatedSyncHandler:
    """执行受控分页读取、逐页持久化和成功后的水位推进。"""

    def __init__(
        self,
        fetcher: SyncPageFetcher,
        *,
        sink: SyncPageSink | None = None,
        watermark_store: SyncWatermarkStore | None = None,
        max_pages: int = 100,
        max_retries: int = 3,
        retry_base_seconds: float = 0.0,
    ) -> None:
        if max_pages < 1 or max_pages > 1000:
            raise ValueError("max_pages 必须在 1 到 1000 之间")
        if max_retries < 0 or max_retries > 10:
            raise ValueError("max_retries 必须在 0 到 10 之间")
        self._fetcher = fetcher
        self._sink = sink
        self._watermark_store = watermark_store
        self._max_pages = max_pages
        self._max_retries = max_retries
        self._retry_base_seconds = max(retry_base_seconds, 0.0)

    async def run(self, job: SyncJob) -> SyncResult:
        cursor: str | None = None
        seen_cursors: set[str | None] = set()
        processed = 0
        for _ in range(self._max_pages):
            if cursor in seen_cursors:
                raise RuntimeError("上游游标未前进，已停止同步")
            seen_cursors.add(cursor)
            page = await self._fetch_page_with_retry(job, cursor)
            # 保存失败时直接抛错，Worker 会让任务失败且不推进长期水位。
            if self._sink is not None:
                await self._sink.save_page(job=job, page=page)
            processed += len(page.items)
            if page.next_cursor is None:
                if self._watermark_store is not None:
                    await self._watermark_store.advance(job=job, cursor=None)
                return SyncResult(processed_count=processed, failure_count=0)
            cursor = page.next_cursor
        raise RuntimeError("同步超过最大分页数，已停止同步")

    async def _fetch_page_with_retry(self, job: SyncJob, cursor: str | None) -> SyncPage:
        for attempt in range(self._max_retries + 1):
            try:
                return await self._fetcher.fetch_page(
                    workspace_id=job.workspace_id,
                    resource_type=job.resource_type,
                    cursor=cursor,
                )
            except RetryableSyncError as error:
                if attempt >= self._max_retries:
                    raise RuntimeError("上游重试次数耗尽") from error
                delay = max(error.retry_after_seconds, self._retry_base_seconds * (2**attempt))
                if delay:
                    await asyncio.sleep(delay)
        raise AssertionError("重试循环未返回")
