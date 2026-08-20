"""按版本化佣金规则和 FBS 物流模板计算分 SKU 预计贡献利润。"""

from dataclasses import dataclass
from datetime import date

ALGORITHM_VERSION = "sku-profit-v1"


class ProfitCalculationError(ValueError):
    """表示输入或费率目录不足以产生可信、可追溯的利润结果。"""


@dataclass(frozen=True, slots=True)
class RateTrace:
    """记录参与计算的规则版本、来源和生效时间，防止结果失去口径。"""

    version: str
    source: str
    effective_at: str


@dataclass(frozen=True, slots=True)
class CommissionRule:
    """定义一个 Ozon 类目在特定版本下的佣金费率。"""

    category_id: str
    rate_bps: int
    trace: RateTrace


@dataclass(frozen=True, slots=True)
class LogisticsBand:
    """定义计费重量上限（含）及该分档对应的单件 FBS 物流费。"""

    max_chargeable_weight_g: int
    fee_minor: int
    additional_fee_minor: int = 0
    additional_step_g: int = 0
    fee_rate_bps: int = 0


@dataclass(frozen=True, slots=True)
class FbsLogisticsTemplate:
    """定义体积重换算和按计费重量递增匹配的 FBS 物流规则版本。"""

    template_id: str
    volumetric_divisor_cm3_per_kg: int
    bands: tuple[LogisticsBand, ...]
    trace: RateTrace
    fulfillment_type: str = "FBS"
    warehouse_id: str | None = None
    route_id: str | None = None
    region_id: str | None = None
    effective_to: str | None = None


@dataclass(frozen=True, slots=True)
class SkuProfitInput:
    """保存单个 SKU 的价格、成本、规格和待使用物流模板。"""

    sku_id: str
    selling_price_minor: int
    discount_minor: int
    landed_cost_minor: int
    weight_g: int
    length_mm: int
    width_mm: int
    height_mm: int
    logistics_template_id: str
    packaging_minor: int = 0
    payment_rate_bps: int = 0
    ad_rate_bps: int = 0
    return_loss_rate_bps: int = 0
    other_variable_cost_minor: int = 0


@dataclass(frozen=True, slots=True)
class ProductProfitInput:
    """表示同一商品类目下需要按统一规则计算的一组 SKU。"""

    product_name: str
    category_id: str
    skus: tuple[SkuProfitInput, ...]


@dataclass(frozen=True, slots=True)
class SkuProfitResult:
    """返回单 SKU 费用瀑布、利润结论及完整规则追溯信息。"""

    sku_id: str
    transaction_price_minor: int
    net_revenue_minor: int
    landed_cost_minor: int
    commission_minor: int
    logistics_minor: int
    packaging_minor: int
    payment_fee_minor: int
    ad_cost_minor: int
    return_loss_minor: int
    other_variable_cost_minor: int
    contribution_profit_minor: int
    contribution_margin_percent: float | None
    break_even_price_minor: int
    actual_weight_g: int
    volumetric_weight_g: int
    chargeable_weight_g: int
    is_negative: bool
    commission_rate_bps: int
    commission_trace: RateTrace
    logistics_trace: RateTrace
    algorithm_version: str = ALGORITHM_VERSION


def calculate_sku_profits(
    product: ProductProfitInput,
    commission_rules: tuple[CommissionRule, ...],
    logistics_templates: tuple[FbsLogisticsTemplate, ...],
) -> tuple[SkuProfitResult, ...]:
    """为商品的全部 SKU 自动匹配费率并计算同口径利润。

    Args:
        product: 包含类目和一个或多个 SKU 的商品测算输入。
        commission_rules: 本次测算可用的不可变佣金规则版本目录。
        logistics_templates: 本次测算可用的不可变 FBS 物流模板版本目录。

    Returns:
        与输入 SKU 顺序一致的利润结果；每项均携带规则追溯信息。

    Raises:
        ProfitCalculationError: 输入非法、规则缺失/冲突或物流分档无法覆盖时抛出。
    """
    if not product.category_id.strip():
        raise ProfitCalculationError("category_id 不能为空")
    if not product.skus:
        raise ProfitCalculationError("至少需要一个 SKU")
    matched_rules = [rule for rule in commission_rules if rule.category_id == product.category_id]
    if len(matched_rules) != 1:
        detail = "缺少" if not matched_rules else "存在多个"
        raise ProfitCalculationError(f"类目 {product.category_id} {detail}有效佣金规则")
    templates = _select_templates(logistics_templates)
    rule = matched_rules[0]
    _validate_rate("佣金率", rule.rate_bps)
    return tuple(_calculate_sku(sku, rule, templates) for sku in product.skus)


def _calculate_sku(
    sku: SkuProfitInput,
    commission: CommissionRule,
    templates: dict[str, FbsLogisticsTemplate],
) -> SkuProfitResult:
    """校验单个 SKU、匹配物流分档并计算费用瀑布。"""
    _validate_sku(sku, commission.rate_bps)
    template = templates.get(sku.logistics_template_id)
    if template is None:
        raise ProfitCalculationError(
            f"SKU {sku.sku_id} 缺少物流模板 {sku.logistics_template_id}"
        )
    volumetric_weight = _volumetric_weight_g(sku, template)
    chargeable_weight = max(sku.weight_g, volumetric_weight)
    logistics = _match_logistics_fee(sku.sku_id, chargeable_weight, template)
    transaction_price = sku.selling_price_minor - sku.discount_minor
    return_loss = _rate_amount(transaction_price, sku.return_loss_rate_bps)
    net_revenue = transaction_price - return_loss
    commission_amount = _rate_amount(transaction_price, commission.rate_bps)
    payment_fee = _rate_amount(transaction_price, sku.payment_rate_bps)
    ad_cost = _rate_amount(transaction_price, sku.ad_rate_bps)
    profit = (
        net_revenue
        - sku.landed_cost_minor
        - commission_amount
        - logistics
        - sku.packaging_minor
        - payment_fee
        - ad_cost
        - sku.other_variable_cost_minor
    )
    break_even = _break_even_price(sku, commission.rate_bps, logistics)
    margin = round(profit / net_revenue * 100, 2) if net_revenue else None
    return SkuProfitResult(
        sku_id=sku.sku_id,
        transaction_price_minor=transaction_price,
        net_revenue_minor=net_revenue,
        landed_cost_minor=sku.landed_cost_minor,
        commission_minor=commission_amount,
        logistics_minor=logistics,
        packaging_minor=sku.packaging_minor,
        payment_fee_minor=payment_fee,
        ad_cost_minor=ad_cost,
        return_loss_minor=return_loss,
        other_variable_cost_minor=sku.other_variable_cost_minor,
        contribution_profit_minor=profit,
        contribution_margin_percent=margin,
        break_even_price_minor=break_even,
        actual_weight_g=sku.weight_g,
        volumetric_weight_g=volumetric_weight,
        chargeable_weight_g=chargeable_weight,
        is_negative=profit < 0,
        commission_rate_bps=commission.rate_bps,
        commission_trace=commission.trace,
        logistics_trace=template.trace,
    )


def _validate_sku(sku: SkuProfitInput, commission_rate_bps: int) -> None:
    """验证金额、规格和比例边界，避免生成看似精确的无效结果。"""
    if not sku.sku_id.strip():
        raise ProfitCalculationError("sku_id 不能为空")
    if sku.selling_price_minor <= 0:
        raise ProfitCalculationError(f"SKU {sku.sku_id} 售价必须大于 0")
    money = (
        sku.discount_minor,
        sku.landed_cost_minor,
        sku.packaging_minor,
        sku.other_variable_cost_minor,
    )
    if any(value < 0 for value in money):
        raise ProfitCalculationError(f"SKU {sku.sku_id} 金额不能为负数")
    if sku.discount_minor >= sku.selling_price_minor:
        raise ProfitCalculationError(f"SKU {sku.sku_id} 折扣必须小于售价")
    if min(sku.weight_g, sku.length_mm, sku.width_mm, sku.height_mm) <= 0:
        raise ProfitCalculationError(f"SKU {sku.sku_id} 重量和长宽高必须大于 0")
    rates = (
        commission_rate_bps,
        sku.payment_rate_bps,
        sku.ad_rate_bps,
        sku.return_loss_rate_bps,
    )
    for name, rate in zip(("佣金", "支付", "广告", "退货损耗"), rates, strict=True):
        _validate_rate(f"SKU {sku.sku_id} {name}费率", rate)
    if sum(rates) >= 10_000:
        raise ProfitCalculationError(f"SKU {sku.sku_id} 可变费率合计必须小于 100%")


def _validate_rate(name: str, rate_bps: int) -> None:
    """验证基点费率处于 0% 到 100% 的闭区间。"""
    if not 0 <= rate_bps <= 10_000:
        raise ProfitCalculationError(f"{name}必须在 0 到 10000 基点之间")


def _volumetric_weight_g(sku: SkuProfitInput, template: FbsLogisticsTemplate) -> int:
    """使用整数向上取整计算体积重，避免低估边界 SKU 的物流费。"""
    divisor = template.volumetric_divisor_cm3_per_kg
    if divisor <= 0:
        raise ProfitCalculationError(f"物流模板 {template.template_id} 体积重系数必须大于 0")
    volume_mm3 = sku.length_mm * sku.width_mm * sku.height_mm
    return (volume_mm3 + divisor - 1) // divisor


def _match_logistics_fee(
    sku_id: str, chargeable_weight_g: int, template: FbsLogisticsTemplate
) -> int:
    """按递增重量上限选择首个覆盖分档，并验证模板不存在重叠或负费用。"""
    if not template.bands:
        raise ProfitCalculationError(f"物流模板 {template.template_id} 没有费用分档")
    previous = 0
    for band in template.bands:
        if (
            band.max_chargeable_weight_g <= previous
            or band.fee_minor < 0
            or band.additional_fee_minor < 0
            or band.additional_step_g < 0
        ):
            raise ProfitCalculationError(f"物流模板 {template.template_id} 分档必须递增且费用非负")
        lower_bound = previous
        _validate_rate(f"物流模板 {template.template_id} 比例费", band.fee_rate_bps)
        previous = band.max_chargeable_weight_g
        if chargeable_weight_g <= band.max_chargeable_weight_g:
            extra_steps = (
                (chargeable_weight_g - lower_bound + band.additional_step_g - 1)
                // band.additional_step_g
                if band.additional_step_g > 0
                else 0
            )
            return band.fee_minor + extra_steps * band.additional_fee_minor + _rate_amount(
                band.fee_minor, band.fee_rate_bps
            )
    raise ProfitCalculationError(
        f"SKU {sku_id} 计费重量 {chargeable_weight_g}g 超出模板 {template.template_id} 覆盖范围"
    )


def _select_templates(
    templates: tuple[FbsLogisticsTemplate, ...],
) -> dict[str, FbsLogisticsTemplate]:
    """校验模板版本和适用时间，并拒绝同一编号的模糊覆盖。"""
    selected: dict[str, FbsLogisticsTemplate] = {}
    for template in templates:
        if template.template_id in selected:
            raise ProfitCalculationError("同一测算不能包含重复的物流模板编号")
        if template.effective_to is not None:
            try:
                if date.fromisoformat(template.effective_to) < date.fromisoformat(
                    template.trace.effective_at[:10]
                ):
                    raise ProfitCalculationError(
                        f"物流模板 {template.template_id} 生效结束日期早于生效日期"
                    )
            except ValueError as exc:
                raise ProfitCalculationError(
                    f"物流模板 {template.template_id} 日期格式必须为 YYYY-MM-DD"
                ) from exc
        selected[template.template_id] = template
    return selected


def _rate_amount(base_minor: int, rate_bps: int) -> int:
    """按 half-up 规则把比例费用舍入到最小货币单位。"""
    return (base_minor * rate_bps + 5_000) // 10_000


def _break_even_price(sku: SkuProfitInput, commission_rate_bps: int, logistics: int) -> int:
    """用与正式计算相同的逐项舍入规则二分求最低不亏售价。"""
    fixed = (
        sku.landed_cost_minor
        + logistics
        + sku.packaging_minor
        + sku.other_variable_cost_minor
    )
    rates = (
        commission_rate_bps,
        sku.payment_rate_bps,
        sku.ad_rate_bps,
        sku.return_loss_rate_bps,
    )

    def profit_at(price: int) -> int:
        transaction = price - sku.discount_minor
        return transaction - sum(_rate_amount(transaction, rate) for rate in rates) - fixed

    low = sku.discount_minor + 1
    high = max(sku.selling_price_minor, low)
    while profit_at(high) < 0:
        high *= 2
    while low < high:
        middle = (low + high) // 2
        if profit_at(middle) >= 0:
            high = middle
        else:
            low = middle + 1
    return low
