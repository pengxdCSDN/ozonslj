"""说明本模块的职责、边界和主要协作对象。"""

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

FulfillmentType = Literal["FBO", "FBS"]


class StockPosition(BaseModel):
    """商品在一个仓库和履约方式下的当前库存事实。"""

    model_config = ConfigDict(frozen=True)

    offer_id: str = Field(min_length=1)
    warehouse_id: str = Field(min_length=1)
    warehouse_name: str | None = None
    fulfillment_type: FulfillmentType
    available_quantity: int = Field(ge=0)
    reserved_quantity: int = Field(ge=0)
    synced_at: datetime


class StockPositionPage(BaseModel):
    """稳定分页的库存位置列表；游标当前表示已读取记录数。"""

    items: list[StockPosition]
    total: int = Field(ge=0)
    next_cursor: str | None = None
    source: Literal["postgresql"] = "postgresql"


class StockPositionGateway(Protocol):
    """库存位置只读端口；上层不依赖 PostgreSQL 或 Ozon 传输结构。"""

    async def list_stock_positions(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> StockPositionPage:
        """执行 list_stock_positions 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
