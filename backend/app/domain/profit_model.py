"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProfitModelInput:
    """说明 ProfitModelInput 的职责、状态边界和对外协作关系。"""
    selling_price_minor: int
    purchase_cost_minor: int
    fbo_logistics_minor: int
    fbs_logistics_minor: int
    commission_minor: int
    ad_cost_minor: int
    return_loss_minor: int
    fixed_cost_minor: int = 0


@dataclass(frozen=True, slots=True)
class ProfitScenario:
    """说明 ProfitScenario 的职责、状态边界和对外协作关系。"""
    fulfillment_type: str
    contribution_profit_minor: int
    contribution_margin_percent: float
    roi_percent: float
    break_even_units: int | None
    ad_cost_plus_20_profit_minor: int
    purchase_cost_plus_20_profit_minor: int
    logistics_cost_plus_20_profit_minor: int


class ProfitModelGateway(Protocol):
    """说明 ProfitModelGateway 的职责、状态边界和对外协作关系。"""
    async def save_model(
        self,
        *,
        workspace_id: str,
        assumptions: dict[str, object],
        scenarios: tuple[ProfitScenario, ProfitScenario],
    ) -> tuple[ProfitScenario, ProfitScenario]:
        """执行 save_model 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    assumptions: 参数语义、输入边界和安全约束。
    scenarios: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def calculate_profit_model(item: ProfitModelInput) -> tuple[ProfitScenario, ProfitScenario]:
    """执行 calculate_profit_model 的业务流程并返回该流程的结果。

Args:
    item: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    _validate_inputs(item)
    return (
        _scenario("FBO", item, item.fbo_logistics_minor),
        _scenario("FBS", item, item.fbs_logistics_minor),
    )


def _validate_inputs(item: ProfitModelInput) -> None:
    """执行内部步骤 _validate_inputs，供同一模块的公开流程复用。

Args:
    item: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    values = (
        item.selling_price_minor,
        item.purchase_cost_minor,
        item.fbo_logistics_minor,
        item.fbs_logistics_minor,
        item.commission_minor,
        item.ad_cost_minor,
        item.return_loss_minor,
        item.fixed_cost_minor,
    )
    if any(value < 0 for value in values):
        raise ValueError("利润模型输入不能为负数")
    if item.selling_price_minor == 0:
        raise ValueError("售价必须大于零，才能计算利润率")


def _scenario(kind: str, item: ProfitModelInput, logistics: int) -> ProfitScenario:
    """执行内部步骤 _scenario，供同一模块的公开流程复用。

Args:
    kind: 参数语义、输入边界和安全约束。
    item: 参数语义、输入边界和安全约束。
    logistics: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    profit = _profit(item, logistics, item.ad_cost_minor, item.purchase_cost_minor)
    cost = (
        item.purchase_cost_minor
        + logistics
        + item.commission_minor
        + item.ad_cost_minor
        + item.return_loss_minor
    )
    return ProfitScenario(
        kind,
        profit,
        round(profit / item.selling_price_minor * 100, 2) if item.selling_price_minor else 0.0,
        round(profit / cost * 100, 2) if cost else 0.0,
        (item.fixed_cost_minor + profit - 1) // profit if profit > 0 else None,
        _profit(item, logistics, item.ad_cost_minor * 1.2, item.purchase_cost_minor),
        _profit(item, logistics, item.ad_cost_minor, item.purchase_cost_minor * 1.2),
        _profit(item, logistics * 1.2, item.ad_cost_minor, item.purchase_cost_minor),
    )


def _profit(item: ProfitModelInput, logistics: float, ad_cost: float, purchase: float) -> int:
    """执行内部步骤 _profit，供同一模块的公开流程复用。

Args:
    item: 参数语义、输入边界和安全约束。
    logistics: 参数语义、输入边界和安全约束。
    ad_cost: 参数语义、输入边界和安全约束。
    purchase: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return round(
        item.selling_price_minor
        - purchase
        - logistics
        - item.commission_minor
        - ad_cost
        - item.return_loss_minor
    )
