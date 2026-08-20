"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import date
from typing import Literal, cast

FulfillmentType = Literal["FBO", "FBS"]


@dataclass(frozen=True, slots=True)
class SellerFulfillmentSyncItem:
    """说明 SellerFulfillmentSyncItem 的职责、状态边界和对外协作关系。"""
    posting_id: str
    fulfillment_type: FulfillmentType
    status: str
    shipment_date: str | None
    item_count: int
    total_quantity: int
    source: str


@dataclass(frozen=True, slots=True)
class SellerFulfillmentSyncPreview:
    """说明 SellerFulfillmentSyncPreview 的职责、状态边界和对外协作关系。"""
    items: list[SellerFulfillmentSyncItem]
    total: int
    next_cursor: str | None
    source: str
    credentials_required: bool
    dry_run: bool


def map_seller_fulfillment_response(payload: dict[str, object]) -> SellerFulfillmentSyncPreview:
    """执行 map_seller_fulfillment_response 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("Seller 履约响应 items 必须是数组")
    items: list[SellerFulfillmentSyncItem] = []
    seen_posting_ids: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("Seller 履约响应包含无效履约单")
        posting_id = _text(raw, "posting_id")
        if posting_id in seen_posting_ids:
            raise ValueError("Seller 履约响应包含重复 posting")
        seen_posting_ids.add(posting_id)
        kind_value = _text(raw, "fulfillment_type")
        if kind_value not in {"FBO", "FBS"}:
            raise ValueError("履约类型必须是 FBO 或 FBS")
        kind = cast(FulfillmentType, kind_value)  # 白名单校验后收窄为领域枚举。
        status = _text(raw, "status")
        shipment = raw.get("shipment_date")
        if shipment is not None:
            if not isinstance(shipment, str):
                raise ValueError("shipment_date 格式无效")
            try:
                date.fromisoformat(shipment)
            except ValueError as error:
                raise ValueError("shipment_date 必须是 ISO 日期") from error
        items.append(SellerFulfillmentSyncItem(
            posting_id, kind, status, shipment,
            _quantity(raw, "item_count"), _quantity(raw, "total_quantity"), "official_private",
        ))
    total = payload.get("total", len(items))
    if isinstance(total, bool) or not isinstance(total, int) or total < len(items):
        raise ValueError("Seller 履约响应 total 无效")
    cursor = payload.get("next_cursor")
    if cursor is not None and (not isinstance(cursor, str) or not cursor.strip()):
        raise ValueError("Seller 履约响应 next_cursor 无效")
    return SellerFulfillmentSyncPreview(items, total, cursor, "seller_api", True, True)


def _text(raw: dict[str, object], field: str) -> str:
    """执行内部步骤 _text，供同一模块的公开流程复用。

Args:
    raw: 参数语义、输入边界和安全约束。
    field: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Seller 履约字段 {field} 无效")
    return value.strip()


def _quantity(raw: dict[str, object], field: str) -> int:
    """执行内部步骤 _quantity，供同一模块的公开流程复用。

Args:
    raw: 参数语义、输入边界和安全约束。
    field: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    value = raw.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Seller 履约字段 {field} 必须是非负整数")
    return value
