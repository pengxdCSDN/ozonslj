import pytest

from backend.app.application.seller_sync_processor import SyncPage, process_seller_pages


class RepeatingReader:
    async def read_page(self, *, cursor: str | None) -> SyncPage:
        return SyncPage(items=[], next_cursor="same")


class EmptySink:
    async def save_page(self, *, items: list[dict[str, object]]) -> None:
        return None


@pytest.mark.asyncio
async def test_processor_stops_repeating_cursor() -> None:
    with pytest.raises(ValueError, match="游标重复"):
        await process_seller_pages(RepeatingReader(), EmptySink(), max_pages=5)


@pytest.mark.asyncio
async def test_processor_rejects_boolean_limits() -> None:
    with pytest.raises(ValueError):
        await process_seller_pages(RepeatingReader(), EmptySink(), max_pages=True)  # type: ignore[arg-type]
