from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.dependencies import get_product_offer_gateway
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.product_offers import router as product_offers_router
from backend.app.infrastructure.local.sqlite_product_offers import (
    SqliteProductOfferGateway,
)
from backend.app.infrastructure.ozon.gateway import STUB_PRODUCT_OFFERS


def create_app(*, database_path: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="Ozon Seller Operations API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type", "X-Request-Id"],
    )
    app.include_router(health_router)
    app.include_router(product_offers_router)
    if database_path is not None:
        gateway = SqliteProductOfferGateway(database_path, STUB_PRODUCT_OFFERS)
        app.dependency_overrides[get_product_offer_gateway] = lambda: gateway
    return app


app = create_app()
