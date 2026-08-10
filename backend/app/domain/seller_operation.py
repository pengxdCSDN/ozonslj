from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["read", "reversible_write", "destructive_write"]
OperationResult = Literal["success", "partial", "failed", "cancelled"]


class SellerOperationSummary(BaseModel):
    """面向运营人员的脱敏操作审计摘要。"""

    model_config = ConfigDict(frozen=True)

    operation_id: str = Field(min_length=1)
    operation_type: str = Field(min_length=1)
    risk_level: RiskLevel
    target_type: str | None = None
    target_count: int = Field(ge=0)
    request_id: str | None = None
    result: OperationResult
    occurred_at: datetime


class SellerOperationPage(BaseModel):
    items: list[SellerOperationSummary]
    total: int = Field(ge=0)
    next_cursor: str | None = None
    source: Literal["postgresql"] = "postgresql"


class SellerOperationGateway(Protocol):
    """操作审计只读端口；敏感 detail 永远不属于列表契约。"""

    async def list_seller_operations(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> SellerOperationPage: ...
