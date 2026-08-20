"""通过 Ozon Seller API 只读读取商品、SKU 属性和价格佣金。"""

from typing import Any, cast

import httpx

from backend.app.domain.ozon_product_catalog import ProductCatalogPage, ProductSkuFact
from backend.app.domain.store_workspace import (
    OzonAuthenticationError,
    OzonCredentials,
    OzonMalformedResponseError,
    OzonPermissionError,
    OzonRateLimitError,
    OzonTemporaryError,
)

_PRODUCT_LIST_PATH = "/v3/product/list"
_PRODUCT_ATTRIBUTES_PATH = "/v4/product/info/attributes"
_PRODUCT_PRICES_PATH = "/v5/product/info/prices"


class HttpOzonProductCatalogGateway:
    """读取 Seller API 商品目录并合并属性、价格和佣金字段。

    该适配器只负责传输和标准化，不把 Ozon JSON 结构泄漏到领域层；所有请求均由
    后端凭据对象构造，扩展端不会接触 Client-Id 或 Api-Key。
    """

    def __init__(
        self,
        base_url: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """初始化只读 HTTP 适配器。

        Args:
            base_url: Ozon Seller API 服务端地址，必须是受控配置而非用户输入。
            transport: 测试用 HTTPX 传输替身；生产环境使用默认网络传输。

        Returns:
            无返回值。
        """
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    async def list_skus(
        self,
        *,
        credentials: object,
        cursor: str | None,
        limit: int,
    ) -> ProductCatalogPage:
        """读取商品列表并补齐规格、价格和当前佣金信息。

        Args:
            credentials: 必须是后端 `OzonCredentials`；不会记录或返回其字段。
            cursor: Ozon 商品列表分页游标，首次读取为 None。
            limit: 单次读取数量，范围为 1～100。

        Returns:
            标准化 SKU 页面；缺失的 Ozon 字段以 None 表示，供上层展示待补数据。

        Raises:
            ValueError: 凭据对象类型、游标或数量不符合边界时抛出。
            OzonAuthenticationError: Ozon 返回 401。
            OzonPermissionError: Ozon 返回 403。
            OzonRateLimitError: Ozon 返回 429。
            OzonTemporaryError: 网络、超时或 5xx 错误。
            OzonMalformedResponseError: 成功响应无法解析为预期结构。
        """
        if not isinstance(credentials, OzonCredentials):
            raise ValueError("商品目录读取必须由后端注入 OzonCredentials")
        if not 1 <= limit <= 100:
            raise ValueError("商品目录单页数量必须在 1 到 100 之间")
        if cursor is not None and not cursor.strip():
            raise ValueError("商品目录分页游标不能为空字符串")
        headers = {"Client-Id": credentials.client_id, "Api-Key": credentials.api_key}
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(15.0),
            transport=self._transport,
        ) as client:
            product_payload = await self._request_json(
                client,
                _PRODUCT_LIST_PATH,
                headers=headers,
                json={"filter": {"visibility": "ALL"}, "last_id": cursor or "", "limit": limit},
            )
            products = _list_of_dicts(product_payload, "items")
            product_ids = [_string(item, "product_id") for item in products]
            attributes = await self._request_json(
                client,
                _PRODUCT_ATTRIBUTES_PATH,
                headers=headers,
                json={"filter": {"product_id": product_ids, "visibility": "ALL"}, "limit": limit},
            ) if product_ids else {"items": []}
            prices = await self._request_json(
                client,
                _PRODUCT_PRICES_PATH,
                headers=headers,
                json={
                    "filter": {"offer_id": [_string(item, "offer_id") for item in products]},
                    "limit": limit,
                },
            ) if products else {"items": []}
        return _merge_catalog(
            products,
            attributes,
            prices,
            _response_value(product_payload, "last_id"),
        )

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> dict[str, Any]:
        """执行单次只读请求并统一转换 HTTPX 和 Ozon 错误。

        Args:
            client: 已配置 Ozon 基地址、超时和测试传输的 HTTPX 客户端。
            path: 代码固定的允许读取路径，不接受外部任意 URL。
            headers: 后端生成的认证头；不会写入日志。
            json: 当前官方接口所需的结构化请求体。

        Returns:
            已验证为 JSON 对象的 Ozon 响应。

        Raises:
            OzonAuthenticationError: 上游拒绝凭据。
            OzonPermissionError: 凭据无该只读权限。
            OzonRateLimitError: 上游触发限流。
            OzonTemporaryError: 网络、超时或服务端暂时错误。
            OzonMalformedResponseError: 响应不是 JSON 对象。
        """
        try:
            response = await client.post(path, headers=headers, json=json)
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise OzonTemporaryError("暂时无法读取 Ozon 商品数据") from error
        if response.status_code == 401:
            raise OzonAuthenticationError("Ozon 拒绝了商品读取凭据")
        if response.status_code == 403:
            raise OzonPermissionError("当前凭据缺少商品读取权限")
        if response.status_code == 429:
            raise OzonRateLimitError("Ozon 商品读取受到限流")
        if response.status_code >= 500:
            raise OzonTemporaryError("Ozon 商品服务暂时不可用")
        if not response.is_success:
            raise OzonMalformedResponseError(f"Ozon 商品接口返回 HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as error:
            raise OzonMalformedResponseError("Ozon 商品接口返回了非 JSON 响应") from error
        if not isinstance(payload, dict):
            raise OzonMalformedResponseError("Ozon 商品接口响应必须是 JSON 对象")
        return payload


def _merge_catalog(
    products: list[dict[str, Any]],
    attributes_payload: dict[str, Any],
    prices_payload: dict[str, Any],
    next_cursor: object,
) -> ProductCatalogPage:
    """把三个 Seller API 响应合并成 SKU 事实页面。"""
    attributes = {
        _key(item, "id", "product_id"): item
        for item in _list_of_dicts(attributes_payload, "items")
    }
    prices = {
        _key(item, "offer_id"): item
        for item in _list_of_dicts(prices_payload, "items")
    }
    items: list[ProductSkuFact] = []
    for product in products:
        product_id = _string(product, "product_id")
        offer_id = _string(product, "offer_id")
        attribute = attributes.get(product_id, {})
        price = prices.get(offer_id, {})
        dimensions = (
            cast(dict[str, Any], attribute["dimensions"])
            if isinstance(attribute.get("dimensions"), dict)
            else attribute
        )
        items.append(ProductSkuFact(
            offer_id=offer_id,
            ozon_product_id=product_id,
            product_group_id=_optional_string(product, "model_id"),
            name=_optional_string(product, "name") or offer_id,
            category_id=_optional_string(product, "category_id"),
            price_minor=_minor_price(price),
            currency=_optional_string(price, "currency"),
            weight_g=_optional_int(attribute, "weight"),
            length_mm=_optional_int(dimensions, "depth") or _optional_int(dimensions, "length"),
            width_mm=_optional_int(dimensions, "width"),
            height_mm=_optional_int(dimensions, "height"),
            commission_rate_bps=_commission_bps(price),
        ))
    cursor = next_cursor if isinstance(next_cursor, str) and next_cursor.strip() else None
    return ProductCatalogPage(tuple(items), cursor)


def _list_of_dicts(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """读取顶层或 result 容器中的响应数组并拒绝畸形数据。"""
    container: dict[str, Any] = payload
    result = payload.get("result")
    if isinstance(result, dict):
        container = result
        raw = container.get(key, [])
    elif isinstance(result, list) and key == "items":
        raw = result
    else:
        raw = payload.get(key, [])
    if isinstance(raw, dict) and "items" in raw:
        raw = raw["items"]
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        raise OzonMalformedResponseError(f"Ozon 商品响应字段 {key} 必须是对象数组")
    return raw


def _response_value(payload: dict[str, Any], key: str) -> object:
    """读取顶层或 result 容器中的分页字段。"""
    result = payload.get("result")
    if isinstance(result, dict) and key in result:
        return result[key]
    return payload.get(key)


def _key(raw: dict[str, Any], *names: str) -> str:
    """按候选字段读取关联键，找不到时返回空键。"""
    for name in names:
        value = raw.get(name)
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            return str(value)
    return ""


def _string(raw: dict[str, Any], name: str) -> str:
    """读取必需字符串字段并清理空白。"""
    value = raw.get(name)
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not str(value).strip():
        raise OzonMalformedResponseError(f"Ozon 商品字段 {name} 缺失或类型错误")
    return str(value).strip()


def _optional_string(raw: dict[str, Any], name: str) -> str | None:
    """读取可缺失的字符串字段。"""
    value = raw.get(name)
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not str(value).strip():
        return None
    return str(value).strip()


def _optional_int(raw: dict[str, Any], name: str) -> int | None:
    """读取可缺失且必须为正数的规格字段。"""
    value = raw.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _minor_price(raw: dict[str, Any]) -> int | None:
    """把价格对象中的主要价格转换成最小货币单位整数。"""
    value = raw.get("price") or raw.get("marketing_price") or raw.get("marketing_seller_price")
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    try:
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return None


def _commission_bps(raw: dict[str, Any]) -> int | None:
    """读取当前佣金百分比并转换为基点；未知字段保持缺失。"""
    value = raw.get("commission") or raw.get("commission_rate")
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    try:
        percent = float(value)
    except (TypeError, ValueError):
        return None
    return round(percent * 100) if 0 <= percent <= 100 else None
