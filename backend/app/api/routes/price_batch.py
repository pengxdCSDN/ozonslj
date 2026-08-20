"""说明本模块的职责、边界和主要协作对象。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.domain.price_batch import PriceBatchValidation, PriceChange, validate_price_batch

router = APIRouter(prefix="/v1/review/price-batches", tags=["review"])


class PriceChangePayload(BaseModel):
    """说明 PriceChangePayload 的职责、状态边界和对外协作关系。"""
    sku: str = Field(min_length=1, max_length=100)
    old_price_minor: int = Field(ge=0)
    new_price_minor: int = Field(ge=0)
    profit_line_minor: int | None = Field(default=None, ge=0)


class PriceBatchPayload(BaseModel):
    """说明 PriceBatchPayload 的职责、状态边界和对外协作关系。"""
    items: list[PriceChangePayload]
    max_change_percent: int = Field(default=10, ge=0, le=100)


@router.post("/validate", response_model=PriceBatchValidation)
async def validate_batch(payload: PriceBatchPayload) -> PriceBatchValidation:
    """执行 validate_batch 的业务流程并返回该流程的结果。"""
    return validate_price_batch(
        [PriceChange(**item.model_dump()) for item in payload.items],
        max_change_percent=payload.max_change_percent,
    )
