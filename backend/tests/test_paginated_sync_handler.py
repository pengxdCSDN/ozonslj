import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from backend.app.domain.sync_job import SyncJob
from backend.app.infrastructure.ozon.paginated_sync_handler import (
    PaginatedSyncHandler,
    RetryableSyncError,
    SyncPage,
)


def _job() -> SyncJob:
    now = datetime.now(UTC)
    return SyncJob(
        id="sync-1", workspace_id="workspace-1", resource_type="products", status="running",
        processed_count=0, failure_count=0, attempt_count=1, max_attempts=3,
        next_attempt_at=now, created_at=now,
    )


@dataclass
class FakeFetcher:
    pages: dict[str | None, SyncPage]
    cursors: list[str | None]

    async def fetch_page(
        self, *, workspace_id: str, resource_type: str, cursor: str | None
    ) -> SyncPage:
        assert workspace_id == "workspace-1"
        assert resource_type == "products"
        self.cursors.append(cursor)
        return self.pages[cursor]


def test_paginated_handler_counts_all_pages_and_advances_cursor() -> None:
    fetcher = FakeFetcher(
        {None: SyncPage((1, 2), "next"), "next": SyncPage((3,), None)}, []
    )

    result = asyncio.run(PaginatedSyncHandler(fetcher).run(_job()))

    assert result.processed_count == 3
    assert fetcher.cursors == [None, "next"]


def test_paginated_handler_rejects_repeated_cursor() -> None:
    fetcher = FakeFetcher({None: SyncPage((1,), "same"), "same": SyncPage((2,), "same")}, [])

    with pytest.raises(RuntimeError, match="游标未前进"):
        asyncio.run(PaginatedSyncHandler(fetcher).run(_job()))


@dataclass
class RetryingFetcher:
    attempts: int = 0

    async def fetch_page(
        self, *, workspace_id: str, resource_type: str, cursor: str | None
    ) -> SyncPage:
        del workspace_id, resource_type
        self.attempts += 1
        if self.attempts < 3:
            raise RetryableSyncError(retry_after_seconds=0)
        return SyncPage(("item",), None)


def test_paginated_handler_retries_transient_upstream_error() -> None:
    fetcher = RetryingFetcher()

    result = asyncio.run(PaginatedSyncHandler(fetcher, max_retries=2).run(_job()))

    assert result.processed_count == 1
    assert fetcher.attempts == 3


@dataclass
class RecordingSink:
    pages: list[tuple[object, ...]]

    async def save_page(self, *, job: SyncJob, page: SyncPage) -> None:
        assert job.workspace_id == "workspace-1"
        self.pages.append(page.items)


@dataclass
class RecordingWatermark:
    cursors: list[str | None]

    async def advance(self, *, job: SyncJob, cursor: str | None) -> None:
        assert job.resource_type == "products"
        self.cursors.append(cursor)


def test_paginated_handler_saves_each_page_and_advances_watermark_last() -> None:
    fetcher = FakeFetcher(
        {None: SyncPage((1, 2), "next"), "next": SyncPage((3,), None)}, []
    )
    sink = RecordingSink([])
    watermark = RecordingWatermark([])

    result = asyncio.run(
        PaginatedSyncHandler(fetcher, sink=sink, watermark_store=watermark).run(_job())
    )

    assert result.processed_count == 3
    assert sink.pages == [(1, 2), (3,)]
    assert watermark.cursors == [None]
