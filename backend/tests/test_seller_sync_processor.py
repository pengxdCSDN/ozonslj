import pytest

from backend.app.application.seller_sync_processor import SyncPage, process_seller_pages


class Reader:
    def __init__(self) -> None:
        self.cursors: list[str | None] = []
        self.fail_once = True

    async def read_page(self, *, cursor: str | None) -> SyncPage:
        self.cursors.append(cursor)
        if self.fail_once:
            self.fail_once = False
            raise TimeoutError("temporary")
        return SyncPage([{"id": "1"}], None)


class Sink:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    async def save_page(self, *, items: list[dict[str, object]]) -> None:
        self.items.extend(items)


@pytest.mark.asyncio
async def test_processor_retries_and_advances_watermark_after_save() -> None:
    sink = Sink()
    result = await process_seller_pages(Reader(), sink, max_retries=1)
    assert result.processed_count == 1
    assert result.watermark_advanced is True
    assert result.retry_count == 1
    assert sink.items == [{"id": "1"}]
