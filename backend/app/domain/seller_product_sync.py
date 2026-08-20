"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SellerProductSyncItem:
    """说明 SellerProductSyncItem 的职责、状态边界和对外协作关系。"""
    offer_id: str
    ozon_product_id: str | None
    name: str
    price_minor: int
    currency: str
    available_stock: int
    source: str


@dataclass(frozen=True, slots=True)
class SellerProductSyncPreview:
    """说明 SellerProductSyncPreview 的职责、状态边界和对外协作关系。"""
    items: list[SellerProductSyncItem]
    total: int
    next_cursor: str | None
    source: str
    credentials_required: bool
    dry_run: bool


def map_seller_product_response(
    payload: dict[str, object], *, cursor: str | None = None
) -> SellerProductSyncPreview:
    """执行 map_seller_product_response 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("Seller 商品响应 items 必须是数组")
    result: list[SellerProductSyncItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("Seller 商品响应包含无效商品")
        offer_id = _text(raw, "offer_id")
        name = _text(raw, "name")
        currency = _currency(raw)
        product_id = raw.get("ozon_product_id")
        if product_id is not None and (
            isinstance(product_id, bool) or not isinstance(product_id, (int, str))
        ):
            raise ValueError("Seller 商品 ozon_product_id 格式无效")
        price_minor = _nonnegative_int(raw, "price_minor")
        stock = _nonnegative_int(raw, "available_stock")
        result.append(SellerProductSyncItem(
            offer_id,
            str(product_id) if product_id is not None else None,
            name, price_minor, currency, stock, "official_private",
        ))
    total = payload.get("total", len(result))
    if not isinstance(total, int) or total < len(result):
        raise ValueError("Seller 商品响应 total 无效")
    next_cursor = payload.get("next_cursor")
    if next_cursor is not None and (
        not isinstance(next_cursor, str) or not next_cursor.strip()
    ):
        raise ValueError("Seller 商品响应 next_cursor 无效")
    return SellerProductSyncPreview(result, total, next_cursor, "seller_api", True, True)


def _text(raw: dict[str, object], name: str) -> str:
    """执行内部步骤 _text，供同一模块的公开流程复用。

Args:
    raw: 参数语义、输入边界和安全约束。
    name: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    value = raw.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Seller 商品字段 {name} 无效")
    return value.strip()


def _nonnegative_int(raw: dict[str, object], name: str) -> int:
    """执行内部步骤 _nonnegative_int，供同一模块的公开流程复用。

Args:
    raw: 参数语义、输入边界和安全约束。
    name: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    value = raw.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Seller 商品字段 {name} 必须是非负整数")
    return value


def _currency(raw: dict[str, object]) -> str:
    """执行内部步骤 _currency，供同一模块的公开流程复用。

Args:
    raw: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    value = raw.get("currency")
    if not isinstance(value, str) or len(value.strip()) != 3 or not value.strip().isalpha():
        raise ValueError("Seller 商品币种必须是三位字母代码")
    return value.strip().upper()
