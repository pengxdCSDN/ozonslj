from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.product_offers import router as product_offers_router
from backend.app.api.routes.store_workspaces import router as store_workspaces_router
from backend.app.application.identity import IdentityService
from backend.app.config import Settings, get_settings
from backend.app.infrastructure.login_rate_limit import RedisLoginRateLimiter
from backend.app.infrastructure.ozon.gateway import STUB_PRODUCT_OFFERS
from backend.app.infrastructure.postgres.database import PostgresDatabase
from backend.app.infrastructure.postgres.identity import PostgresIdentityGateway
from backend.app.infrastructure.postgres.product_offers import (
    PostgresProductOfferGateway,
)
from backend.app.infrastructure.postgres.workspaces import (
    PostgresStoreWorkspaceGateway,
)
from backend.app.infrastructure.readiness import ServiceReadinessProbe


def create_app(*, settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = PostgresDatabase(
            resolved_settings.postgres_dsn(),
            min_size=resolved_settings.postgres_pool_min_size,
            max_size=resolved_settings.postgres_pool_max_size,
        )
        redis = Redis.from_url(resolved_settings.redis_url, decode_responses=True)
        await database.open(
            seed_offers=STUB_PRODUCT_OFFERS if resolved_settings.ozon_mode == "stub" else ()
        )
        app.state.product_offer_gateway = PostgresProductOfferGateway(database.pool)
        app.state.store_workspace_gateway = PostgresStoreWorkspaceGateway(database.pool)
        app.state.identity_service = IdentityService(PostgresIdentityGateway(database.pool))
        app.state.session_cookie_secure = resolved_settings.session_cookie_secure
        app.state.login_rate_limiter = RedisLoginRateLimiter(
            redis,
            max_attempts=resolved_settings.login_max_attempts,
            window_seconds=resolved_settings.login_window_seconds,
        )
        app.state.readiness_probe = ServiceReadinessProbe(database, redis)
        try:
            yield
        finally:
            await redis.aclose()
            await database.close()

    app = FastAPI(
        title="Ozon Seller Operations API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(store_workspaces_router)
    app.include_router(product_offers_router)
    return app


app = create_app()
