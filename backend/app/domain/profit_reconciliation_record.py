"""可持久化的利润对账批次和明细模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReconciliationSide = Literal["matched", "missing_estimated", "missing_actual"]


class ProfitReconciliationBatch(BaseModel):
    """一次对账运行的可追溯摘要；同一工作区和幂等键只能有一个批次。"""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    source: str = Field(min_length=1)
    status: Literal["completed", "partial", "failed"]
    created_at: datetime


class ProfitReconciliationRecord(BaseModel):
    """订单/SKU 维度的预计与实际利润差异；金额为最小货币单位整数。"""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    batch_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    sku_id: str = Field(min_length=1)
    estimated_profit_minor: int | None = None
    actual_profit_minor: int | None = None
    variance_minor: int | None = None
    side: ReconciliationSide
    source: str = Field(min_length=1)
    created_at: datetime
