from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ValidateInput:
    sku: str
    selling_price_minor: int
    purchase_cost_minor: int
    logistics_cost_minor: int
    commission_minor: int
    ad_cost_minor: int
    return_loss_minor: int
    fixed_launch_cost_minor: int
    competitor_count: int
    own_stock: int
    monthly_sales: int
    certification_required: bool = False


@dataclass(frozen=True, slots=True)
class FulfillmentProfit:
    fulfillment_type: str
    contribution_profit_minor: int
    margin_percent: float
    roi_percent: float
    break_even_units: int | None


@dataclass(frozen=True, slots=True)
class ValidateResult:
    sku: str
    fbo: FulfillmentProfit
    fbs: FulfillmentProfit
    risks: tuple[str, ...]
    incomplete: bool
    incomplete_reasons: tuple[str, ...]


class ValidateResultGateway(Protocol):
    async def save_validation(
        self, *, workspace_id: str, assumptions: dict[str, object], result: ValidateResult
    ) -> ValidateResult: ...

    async def list_validations(
        self, *, workspace_id: str, limit: int
    ) -> list[ValidateResult]: ...


def validate_product(item: ValidateInput) -> ValidateResult:
    """按输入假设评估 SKU；缺少成本时只输出不完整估算，不隐藏默认值。"""
    fbo = _profit("FBO", item, item.logistics_cost_minor)
    fbs = _profit("FBS", item, item.logistics_cost_minor)
    risks: list[str] = []
    if item.competitor_count >= 20:
        risks.append("竞品数量较高")
    if item.own_stock > max(item.monthly_sales, 1) * 2:
        risks.append("库存周转可能偏慢")
    if item.certification_required:
        risks.append("需要人工确认认证要求")
    if item.monthly_sales <= 0:
        risks.append("缺少有效销量窗口")
    incomplete_reasons: list[str] = []
    if item.selling_price_minor <= 0:
        incomplete_reasons.append("selling_price_minor")
    if item.competitor_count <= 0:
        incomplete_reasons.append("competitor_sample")
    if item.monthly_sales <= 0:
        incomplete_reasons.append("monthly_sales")
    incomplete = bool(incomplete_reasons) or any(
        value < 0
        for value in (
            item.purchase_cost_minor,
            item.logistics_cost_minor,
            item.commission_minor,
            item.ad_cost_minor,
            item.return_loss_minor,
        )
    )
    return ValidateResult(item.sku, fbo, fbs, tuple(risks), incomplete, tuple(incomplete_reasons))


def _profit(kind: str, item: ValidateInput, logistics: int) -> FulfillmentProfit:
    cost = (
        item.purchase_cost_minor
        + logistics
        + item.commission_minor
        + item.ad_cost_minor
        + item.return_loss_minor
    )
    profit = item.selling_price_minor - cost
    margin = round(profit / item.selling_price_minor * 100, 2) if item.selling_price_minor else 0.0
    roi = round(profit / cost * 100, 2) if cost > 0 else 0.0
    break_even = (
        (item.fixed_launch_cost_minor + max(profit, 0) - 1) // profit
        if profit > 0
        else None
    )
    return FulfillmentProfit(kind, profit, margin, roi, break_even)
