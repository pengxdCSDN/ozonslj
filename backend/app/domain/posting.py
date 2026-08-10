from datetime import date, datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

FulfillmentType = Literal["FBO", "FBS"]


class PostingSummary(BaseModel):
    """FBO/FBS 履约单脱敏摘要，不包含物流追踪号和商品明细。"""

    model_config = ConfigDict(frozen=True)

    posting_id: str = Field(min_length=1)
    customer_order_id: str | None = None
    ozon_posting_number: str = Field(min_length=1)
    fulfillment_type: FulfillmentType
    status: str = Field(min_length=1)
    shipment_date: date | None = None
    item_count: int = Field(ge=0)
    total_quantity: int = Field(ge=0)
    synced_at: datetime


class PostingPage(BaseModel):
    items: list[PostingSummary]
    total: int = Field(ge=0)
    next_cursor: str | None = None
    source: Literal["postgresql"] = "postgresql"


class PostingGateway(Protocol):
    """履约单只读端口；外部传输结构和写操作不得进入该接口。"""

    async def list_postings(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> PostingPage: ...
