"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CostSensitivityInput:
    """说明 CostSensitivityInput 的职责、状态边界和对外协作关系。"""
    selling_price_minor: int
    purchase_cost_minor: int
    logistics_cost_minor: int
    commission_minor: int
    ad_cost_minor: int
    return_loss_minor: int


@dataclass(frozen=True, slots=True)
class CostSensitivityScenario:
    """说明 CostSensitivityScenario 的职责、状态边界和对外协作关系。"""
    label: str
    change_percent: int
    profit_minor: int
    margin_percent: float


class CostSensitivityGateway(Protocol):
    """说明 CostSensitivityGateway 的职责、状态边界和对外协作关系。"""
    async def save_analysis(
        self,
        *,
        workspace_id: str,
        assumptions: dict[str, object],
        scenarios: tuple[CostSensitivityScenario, ...],
    ) -> tuple[CostSensitivityScenario, ...]:
        """执行 save_analysis 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    assumptions: 参数语义、输入边界和安全约束。
    scenarios: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def analyze_cost_sensitivity(item: CostSensitivityInput) -> tuple[CostSensitivityScenario, ...]:
    """执行 analyze_cost_sensitivity 的业务流程并返回该流程的结果。

Args:
    item: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    _validate(item)
    scenarios = (("成本下降", -20), ("基准", 0), ("成本上升", 20))
    return tuple(_scenario(item, label, change) for label, change in scenarios)


def _validate(item: CostSensitivityInput) -> None:
    """执行内部步骤 _validate，供同一模块的公开流程复用。

Args:
    item: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if item.selling_price_minor <= 0:
        raise ValueError("敏感性分析售价必须大于零")
    if any(
        value < 0
        for value in (
            item.purchase_cost_minor,
            item.logistics_cost_minor,
            item.commission_minor,
            item.ad_cost_minor,
            item.return_loss_minor,
        )
    ):
        raise ValueError("敏感性分析成本不能为负数")


def _scenario(item: CostSensitivityInput, label: str, change: int) -> CostSensitivityScenario:
    """执行内部步骤 _scenario，供同一模块的公开流程复用。

Args:
    item: 参数语义、输入边界和安全约束。
    label: 参数语义、输入边界和安全约束。
    change: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    factor = 1 + change / 100
    cost = (
        item.purchase_cost_minor * factor
        + item.logistics_cost_minor * factor
        + item.commission_minor
        + item.ad_cost_minor * factor
        + item.return_loss_minor
    )
    profit = round(item.selling_price_minor - cost)
    margin = round(profit / item.selling_price_minor * 100, 2) if item.selling_price_minor else 0.0
    return CostSensitivityScenario(label, change, profit, margin)
