"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceChange:
    """说明 PriceChange 的职责、状态边界和对外协作关系。"""
    sku: str
    old_price_minor: int
    new_price_minor: int
    profit_line_minor: int | None = None


@dataclass(frozen=True, slots=True)
class PriceBatchValidation:
    """说明 PriceBatchValidation 的职责、状态边界和对外协作关系。"""
    valid: bool
    total_items: int
    max_items: int
    message: str
    items: list[PriceChange]
    max_change_percent: int


def validate_price_batch(
    items: list[PriceChange], *, max_items: int = 20, max_change_percent: int = 10
) -> PriceBatchValidation:
    """执行 validate_price_batch 的业务流程并返回该流程的结果。"""
    if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
        raise ValueError("批量上限必须为正数")
    if (
        isinstance(max_change_percent, bool)
        or not isinstance(max_change_percent, int)
        or max_change_percent < 0
    ):
        raise ValueError("涨跌幅上限不能为负数")
    normalized_skus = [item.sku.strip().casefold() for item in items]
    unique_skus = len(normalized_skus) == len(set(normalized_skus))
    valid = bool(items) and unique_skus and len(items) <= max_items and all(
        item.sku.strip()
        and item.old_price_minor >= 0
        and item.new_price_minor >= 0
        and (item.profit_line_minor is None or item.new_price_minor >= item.profit_line_minor)
        and (
            
                item.new_price_minor == 0
                if item.old_price_minor == 0
                else abs(item.new_price_minor - item.old_price_minor) * 100
                <= item.old_price_minor * max_change_percent
            
        )
        for item in items
    )
    message = (
        f"批量数量和价格涨跌幅（{max_change_percent}%）校验通过"
        if valid
        else f"价格批次必须包含 1 至 {max_items} 个商品，且单次涨跌不得超过 {max_change_percent}%"
    )
    return PriceBatchValidation(valid, len(items), max_items, message, items, max_change_percent)
