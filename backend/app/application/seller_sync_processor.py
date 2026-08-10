from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SyncPage:
    items: list[dict[str, object]]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class SyncProcessResult:
    processed_count: int
    pages: int
    final_cursor: str | None
    watermark_advanced: bool
    retry_count: int


class SellerPageReader(Protocol):
    async def read_page(self, *, cursor: str | None) -> SyncPage: ...


class SyncPageSink(Protocol):
    async def save_page(self, *, items: list[dict[str, object]]) -> None: ...


async def process_seller_pages(
    reader: SellerPageReader,
    sink: SyncPageSink,
    *,
    initial_cursor: str | None = None,
    max_pages: int = 100,
    max_retries: int = 3,
) -> SyncProcessResult:
    """处理 Seller 分页读取；每页成功保存后才推进游标，失败不会推进长期水位。"""
    if (
        isinstance(max_pages, bool) or not isinstance(max_pages, int)
        or isinstance(max_retries, bool) or not isinstance(max_retries, int)
        or max_pages < 1 or max_retries < 0
    ):
        raise ValueError("同步页数和重试次数必须有效")
    cursor = initial_cursor
    processed = 0
    pages = 0
    retries = 0
    seen_cursors: set[str | None] = set()
    while pages < max_pages:
        if cursor in seen_cursors:
            raise ValueError("Seller 分页游标重复，已停止同步以避免死循环")
        seen_cursors.add(cursor)
        page: SyncPage | None = None
        for attempt in range(max_retries + 1):
            try:
                page = await reader.read_page(cursor=cursor)
                break
            except Exception:
                if attempt >= max_retries:
                    raise
                retries += 1
        if page is None:
            raise RuntimeError("同步读取未返回页面")
        await sink.save_page(items=page.items)
        processed += len(page.items)
        pages += 1
        cursor = page.next_cursor
        if cursor is None:
            return SyncProcessResult(processed, pages, None, True, retries)
    return SyncProcessResult(processed, pages, cursor, False, retries)
