"""通过 Ozon Seller API v1 finance/accrual/by-day 只读同步财务 начисления。"""

from datetime import date, timedelta
from typing import Any, cast

import httpx

from backend.app.domain.ozon_finance_accrual import (
    FinanceAccrualLine,
    FinanceAccrualPage,
    validate_finance_range,
)
from backend.app.domain.store_workspace import (
    OzonAuthenticationError,
    OzonCredentials,
    OzonMalformedResponseError,
    OzonPermissionError,
    OzonRateLimitError,
    OzonTemporaryError,
)

_ACCRUAL_BY_DAY_PATH = "/v1/finance/accrual/by-day"


class HttpOzonFinanceAccrualGateway:
    """读取新版 Ozon 财务 начисления并拆分为订单/SKU 对账明细。"""

    def __init__(self, base_url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """初始化财务只读 HTTP 适配器。"""
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    async def list_accruals(
        self,
        *,
        credentials: object,
        date_from: date,
        date_to: date,
    ) -> FinanceAccrualPage:
        """按天翻页读取财务 начисления并标准化金额。

        Args:
            credentials: 后端注入的 OzonCredentials，不会写入日志或响应。
            date_from: 包含在同步范围内的 UTC 日期。
            date_to: 包含在同步范围内的 UTC 日期，最多与开始日期相差 30 天。

        Returns:
            按来源日期和 Ozon 事实标识稳定排列的财务明细。

        Raises:
            ValueError: 凭据类型或日期范围不合法。
            OzonAuthenticationError: Ozon 返回 401。
            OzonPermissionError: Ozon 返回 403。
            OzonRateLimitError: Ozon 返回 429。
            OzonTemporaryError: 网络、超时或 5xx 错误。
            OzonMalformedResponseError: 成功响应不符合财务接口结构。
        """
        if not isinstance(credentials, OzonCredentials):
            raise ValueError("财务同步必须由后端注入 OzonCredentials")
        validate_finance_range(date_from, date_to)
        headers = {"Client-Id": credentials.client_id, "Api-Key": credentials.api_key}
        lines: list[FinanceAccrualLine] = []
        dates: list[str] = []
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(20.0),
            transport=self._transport,
        ) as client:
            current = date_from
            while current <= date_to:
                last_id = ""
                dates.append(current.isoformat())
                while True:
                    payload = await self._request_json(
                        client,
                        headers=headers,
                        json={"date": current.isoformat(), "last_id": last_id},
                    )
                    accruals = payload.get("accruals")
                    if not isinstance(accruals, list) or any(
                        not isinstance(item, dict) for item in accruals
                    ):
                        raise OzonMalformedResponseError("Ozon 财务响应 accruals 必须是对象数组")
                    for index, accrual in enumerate(accruals):
                        lines.extend(_normalize_accrual(accrual, current.isoformat(), index))
                    next_id = payload.get("last_id")
                    if not isinstance(next_id, str) or not next_id.strip() or next_id == last_id:
                        break
                    last_id = next_id
                current += timedelta(days=1)
        return FinanceAccrualPage(tuple(lines), tuple(dates), "ozon_finance_accrual_v1")

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> dict[str, Any]:
        """执行单次财务只读请求并统一转换上游错误。"""
        try:
            response = await client.post(_ACCRUAL_BY_DAY_PATH, headers=headers, json=json)
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise OzonTemporaryError("暂时无法读取 Ozon 财务数据") from error
        if response.status_code == 401:
            raise OzonAuthenticationError("Ozon 拒绝了财务读取凭据")
        if response.status_code == 403:
            raise OzonPermissionError("当前凭据缺少财务读取权限")
        if response.status_code == 429:
            raise OzonRateLimitError("Ozon 财务读取受到限流")
        if response.status_code >= 500:
            raise OzonTemporaryError("Ozon 财务服务暂时不可用")
        if not response.is_success:
            raise OzonMalformedResponseError(f"Ozon 财务接口返回 HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as error:
            raise OzonMalformedResponseError("Ozon 财务接口返回非 JSON") from error
        if not isinstance(payload, dict):
            raise OzonMalformedResponseError("Ozon 财务接口响应必须是 JSON 对象")
        return payload


def _normalize_accrual(
    accrual: dict[str, Any], accrual_date: str, index: int
) -> list[FinanceAccrualLine]:
    """把一个 Ozon начисление拆成商品、物流服务和非商品费用行。"""
    posting = (
        cast(dict[str, Any], accrual.get("posting"))
        if isinstance(accrual.get("posting"), dict)
        else {}
    )
    order_id = _text(posting.get("posting_number"))
    base_id = _text(accrual.get("type_id")) or f"{accrual_date}-{index}"
    lines: list[FinanceAccrualLine] = []
    products = posting.get("products", []) if isinstance(posting.get("products"), list) else []
    for product_index, product in enumerate(products):
        if not isinstance(product, dict):
            continue
        commission = _as_dict(product.get("commission"))
        sku_id = _text(product.get("sku"))
        lines.append(
            _line(
                base_id,
                accrual_date,
                order_id,
                sku_id,
                "sale",
                _money(commission.get("seller_price")),
                product_index,
            )
        )
        lines.append(
            _line(
                base_id,
                accrual_date,
                order_id,
                sku_id,
                "commission",
                _money(commission.get("sale_commission")),
                product_index + 1000,
            )
        )
        delivery = _as_dict(product.get("delivery"))
        services = (
            delivery.get("services", []) if isinstance(delivery.get("services"), list) else []
        )
        for service_index, service in enumerate(services):
            if isinstance(service, dict):
                lines.append(
                    _line(
                        base_id,
                        accrual_date,
                        order_id,
                        sku_id,
                        "logistics",
                        _money(service.get("accrued")),
                        service_index + 2000,
                    )
                )
    non_item = _as_dict(accrual.get("non_item_fee"))
    if non_item:
        lines.append(
            _line(
                base_id,
                accrual_date,
                order_id,
                None,
                "other",
                _money(non_item.get("accrued")),
                3000,
            )
        )
    return [line for line in lines if line.amount_minor != 0]


def _line(
    base_id: str,
    accrual_date: str,
    order_id: str | None,
    sku_id: str | None,
    category: str,
    amount: int,
    suffix: int,
) -> FinanceAccrualLine:
    """创建一条带稳定来源标识的财务明细。"""
    return FinanceAccrualLine(
        f"{base_id}-{suffix}",
        accrual_date,
        order_id,
        sku_id,
        category,
        amount,
        "RUB",
        "ozon_finance_accrual_v1",
    )


def _text(value: object) -> str | None:
    """读取外部标识文本并保留原始字符串语义。"""
    return str(value).strip() if isinstance(value, (str, int)) and str(value).strip() else None


def _as_dict(value: object) -> dict[str, Any]:
    """把可选上游对象收窄为可安全读取的字典。"""
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _money(value: object) -> int:
    """把 Ozon 金额字符串/数字转换为最小货币单位整数。"""
    try:
        return (
            round(float(value) * 100)
            if isinstance(value, (str, int, float)) and not isinstance(value, bool)
            else 0
        )
    except (TypeError, ValueError):
        return 0
