from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CostSensitivityInput:
    selling_price_minor: int
    purchase_cost_minor: int
    logistics_cost_minor: int
    commission_minor: int
    ad_cost_minor: int
    return_loss_minor: int


@dataclass(frozen=True, slots=True)
class CostSensitivityScenario:
    label: str
    change_percent: int
    profit_minor: int
    margin_percent: float


class CostSensitivityGateway(Protocol):
    async def save_analysis(
        self,
        *,
        workspace_id: str,
        assumptions: dict[str, object],
        scenarios: tuple[CostSensitivityScenario, ...],
    ) -> tuple[CostSensitivityScenario, ...]: ...


def analyze_cost_sensitivity(item: CostSensitivityInput) -> tuple[CostSensitivityScenario, ...]:
    _validate(item)
    scenarios = (("成本下降", -20), ("基准", 0), ("成本上升", 20))
    return tuple(_scenario(item, label, change) for label, change in scenarios)


def _validate(item: CostSensitivityInput) -> None:
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
