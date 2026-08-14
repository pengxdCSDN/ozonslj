from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SellerStockSyncItem:
    offer_id: str
    warehouse_id: str
    available_quantity: int
    reserved_quantity: int
    source: str


@dataclass(frozen=True, slots=True)
class SellerStockSyncPreview:
    items: list[SellerStockSyncItem]
    total: int
    next_cursor: str | None
    source: str
    credentials_required: bool
    dry_run: bool


def map_seller_stock_response(payload: dict[str, object]) -> SellerStockSyncPreview:
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("Seller 库存响应 items 必须是数组")
    items: list[SellerStockSyncItem] = []
    seen_keys: set[tuple[str, str]] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("Seller 库存响应包含无效仓位")
        offer_id = _text(raw, "offer_id")
        warehouse_id = _text(raw, "warehouse_id")
        available = _quantity(raw, "available_quantity")
        reserved = _quantity(raw, "reserved_quantity")
        key = (offer_id, warehouse_id)
        if key in seen_keys:
            raise ValueError("Seller 库存响应包含重复商品仓库快照")
        seen_keys.add(key)
        items.append(SellerStockSyncItem(
            offer_id, warehouse_id, available, reserved, "official_private"
        ))
    total = payload.get("total", len(items))
    if isinstance(total, bool) or not isinstance(total, int) or total < len(items):
        raise ValueError("Seller 库存响应 total 无效")
    cursor = payload.get("next_cursor")
    if cursor is not None and (not isinstance(cursor, str) or not cursor.strip()):
        raise ValueError("Seller 库存响应 next_cursor 无效")
    return SellerStockSyncPreview(items, total, cursor, "seller_api", True, True)


def _text(raw: dict[str, object], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Seller 库存字段 {field} 无效")
    return value.strip()


def _quantity(raw: dict[str, object], field: str) -> int:
    value = raw.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Seller 库存字段 {field} 必须是非负整数")
    return value
