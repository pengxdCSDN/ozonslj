from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProductOfferSource = Literal["ozon", "postgres", "stub"]


class ProductOffer(BaseModel):
    model_config = ConfigDict(frozen=True)

    offer_id: str = Field(min_length=1)
    ozon_product_id: str | None = None
    name: str = Field(min_length=1)
    price: Decimal = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    available_stock: int = Field(ge=0)


class ProductOfferPage(BaseModel):
    items: list[ProductOffer]
    total: int = Field(ge=0)
    next_cursor: str | None = None
    source: ProductOfferSource
