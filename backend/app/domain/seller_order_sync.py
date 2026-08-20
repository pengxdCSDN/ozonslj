"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SellerOrderSyncItem:
    """说明 SellerOrderSyncItem 的职责、状态边界和对外协作关系。"""
    order_id: str
    ordered_at: str
    status: str
    total_amount_minor: int
    currency: str
    item_count: int
    source: str


@dataclass(frozen=True, slots=True)
class SellerOrderSyncPreview:
    """说明 SellerOrderSyncPreview 的职责、状态边界和对外协作关系。"""
    items: list[SellerOrderSyncItem]
    total: int
    next_cursor: str | None
    source: str
    credentials_required: bool
    dry_run: bool


def map_seller_order_response(payload: dict[str, object]) -> SellerOrderSyncPreview:
    """执行 map_seller_order_response 的业务流程并返回该流程的结果。"""
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("Seller 订单响应 items 必须是数组")
    items: list[SellerOrderSyncItem] = []
    seen_order_ids: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("Seller 订单响应包含无效订单")
        order_id = _text(raw, "order_id")
        if order_id in seen_order_ids:
            raise ValueError("Seller 订单响应包含重复订单")
        seen_order_ids.add(order_id)
        ordered_at = _text(raw, "ordered_at")
        try:
            datetime.fromisoformat(ordered_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("Seller 订单 ordered_at 必须是 ISO 时间") from error
        status = _text(raw, "status")
        currency = _currency(raw)
        total_amount = _quantity(raw, "total_amount_minor")
        item_count = _quantity(raw, "item_count")
        items.append(SellerOrderSyncItem(
            order_id, ordered_at, status, total_amount, currency, item_count, "official_private"
        ))
    total = payload.get("total", len(items))
    if isinstance(total, bool) or not isinstance(total, int) or total < len(items):
        raise ValueError("Seller 订单响应 total 无效")
    cursor = payload.get("next_cursor")
    if cursor is not None and (not isinstance(cursor, str) or not cursor.strip()):
        raise ValueError("Seller 订单响应 next_cursor 无效")
    return SellerOrderSyncPreview(items, total, cursor, "seller_api", True, True)


def _text(raw: dict[str, object], field: str) -> str:
    """执行内部步骤 _text，供同一模块的公开流程复用。"""
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Seller 订单字段 {field} 无效")
    return value.strip()


def _quantity(raw: dict[str, object], field: str) -> int:
    """执行内部步骤 _quantity，供同一模块的公开流程复用。"""
    value = raw.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Seller 订单字段 {field} 必须是非负整数")
    return value


def _currency(raw: dict[str, object]) -> str:
    """执行内部步骤 _currency，供同一模块的公开流程复用。"""
    value = raw.get("currency")
    if not isinstance(value, str) or len(value.strip()) != 3 or not value.strip().isalpha():
        raise ValueError("Seller 订单币种必须是三位字母代码")
    return value.strip().upper()
