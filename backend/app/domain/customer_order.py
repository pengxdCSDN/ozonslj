"""说明本模块的职责、边界和主要协作对象。"""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class CustomerOrder(BaseModel):
    """供运营查询的脱敏客户订单摘要，不包含买家个人信息。"""

    model_config = ConfigDict(frozen=True)

    order_id: str = Field(min_length=1)
    ozon_order_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    total_amount: Decimal = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    ordered_at: datetime
    synced_at: datetime


class CustomerOrderPage(BaseModel):
    """按下单时间倒序返回的稳定分页订单摘要。"""

    items: list[CustomerOrder]
    total: int = Field(ge=0)
    next_cursor: str | None = None
    source: Literal["postgresql"] = "postgresql"


class CustomerOrderGateway(Protocol):
    """客户订单只读端口；禁止向调用方暴露原始上游响应。"""

    async def list_customer_orders(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> CustomerOrderPage:
        """执行 list_customer_orders 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
