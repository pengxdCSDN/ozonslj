from functools import lru_cache

from backend.app.config import get_settings
from backend.app.infrastructure.local.sqlite_product_offers import (
    SqliteProductOfferGateway,
)
from backend.app.infrastructure.ozon.gateway import (
    STUB_PRODUCT_OFFERS,
    ProductOfferGateway,
)


@lru_cache
def get_product_offer_gateway() -> ProductOfferGateway:
    return SqliteProductOfferGateway(
        get_settings().database_path,
        STUB_PRODUCT_OFFERS,
    )
