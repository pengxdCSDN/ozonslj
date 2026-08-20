"""Ozon 新版财务 начисления 领域端口和标准化事实模型。"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol


@dataclass(frozen=True)
class FinanceAccrualLine:
    """表示一条可用于利润对账的 Ozon 财务费用事实。"""

    accrual_id: str
    accrual_date: str
    order_id: str | None
    sku_id: str | None
    category: str
    amount_minor: int
    currency: str
    source: str


@dataclass(frozen=True)
class FinanceAccrualPage:
    """表示指定日期范围内的一页财务事实和同步游标。"""

    lines: tuple[FinanceAccrualLine, ...]
    dates: tuple[str, ...]
    source: str


class OzonFinanceAccrualGateway(Protocol):
    """定义后端只读拉取 Ozon 财务 начисления 的端口。"""

    async def list_accruals(
        self, *, credentials: object, date_from: date, date_to: date
    ) -> FinanceAccrualPage:
        """按日期范围拉取并标准化财务 начисления。"""


def validate_finance_range(date_from: date, date_to: date) -> None:
    """校验财务同步日期范围不反向且不超过 31 天。"""
    if date_to < date_from:
        raise ValueError("财务同步结束日期不能早于开始日期")
    if date_to - date_from > timedelta(days=30):
        raise ValueError("单次财务同步最多覆盖 31 个自然日")
