"""说明本模块的职责、边界和主要协作对象。"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProductOfferSource = Literal["ozon", "postgresql", "stub"]


class ProductOffer(BaseModel):
    """说明 ProductOffer 的职责、状态边界和对外协作关系。"""
    model_config = ConfigDict(frozen=True)

    offer_id: str = Field(min_length=1)
    ozon_product_id: str | None = None
    name: str = Field(min_length=1)
    price: Decimal = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    available_stock: int = Field(ge=0)


class ProductOfferPage(BaseModel):
    """说明 ProductOfferPage 的职责、状态边界和对外协作关系。"""
    items: list[ProductOffer]
    total: int = Field(ge=0)
    next_cursor: str | None = None
    source: ProductOfferSource
