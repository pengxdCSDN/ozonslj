"""Seller 分页同步编排：成功落库后推进游标，并限制重试和循环。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SyncPage:
    """表示一次 Seller 分页读取结果及下一页游标。"""
    items: list[dict[str, object]]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class SyncProcessResult:
    """记录分页同步处理量、最终游标、水位和重试结果。"""
    processed_count: int
    pages: int
    final_cursor: str | None
    watermark_advanced: bool
    retry_count: int


class SellerPageReader(Protocol):
    """定义 Seller 分页读取适配器必须提供的接口。"""

    async def read_page(self, *, cursor: str | None) -> SyncPage:
        """读取指定游标的单页数据。

Args:
    cursor: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        ...


class SyncPageSink(Protocol):
    """定义成功读取的 Seller 页面事实落库接口。"""

    async def save_page(self, *, items: list[dict[str, object]]) -> None:
        """保存当前页事实；调用方随后才推进同步游标。

Args:
    items: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        ...


async def process_seller_pages(
    reader: SellerPageReader,
    sink: SyncPageSink,
    *,
    initial_cursor: str | None = None,
    max_pages: int = 100,
    max_retries: int = 3,
) -> SyncProcessResult:
    """处理 Seller 分页读取；每页成功保存后才推进游标，失败不会推进长期水位。

Args:
    reader: 参数语义、输入边界和安全约束。
    sink: 参数语义、输入边界和安全约束。
    initial_cursor: 参数语义、输入边界和安全约束。
    max_pages: 参数语义、输入边界和安全约束。
    max_retries: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
    RuntimeError: 业务约束或外部依赖失败时抛出。
"""
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
