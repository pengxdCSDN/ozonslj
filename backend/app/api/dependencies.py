from typing import Annotated, Protocol, cast

from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from backend.app.application.identity import IdentityService
from backend.app.application.seller_accounts import SellerAccountService
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.store_workspace import StoreWorkspaceGateway
from backend.app.domain.sync_job import SyncJobGateway
from backend.app.infrastructure.ozon.gateway import ProductOfferGateway


class ReadinessProbe(Protocol):
    """定义 API 就绪检查所需的最小依赖能力。"""

    async def check(self) -> None: ...


class LoginRateLimiter(Protocol):
    async def retry_after(self, email: str, client_key: str) -> int | None: ...

    async def record_failure(self, email: str, client_key: str) -> None: ...

    async def clear(self, email: str, client_key: str) -> None: ...


def get_product_offer_gateway(request: Request) -> ProductOfferGateway:
    """从应用生命周期状态获取 PostgreSQL 商品仓储。"""

    return cast(ProductOfferGateway, request.app.state.product_offer_gateway)


def get_store_workspace_gateway(request: Request) -> StoreWorkspaceGateway:
    """从应用生命周期状态获取 PostgreSQL 工作区仓储。"""

    return cast(StoreWorkspaceGateway, request.app.state.store_workspace_gateway)


def get_sync_job_gateway(request: Request) -> SyncJobGateway:
    """从应用生命周期状态获取 PostgreSQL 同步任务仓储。"""

    return cast(SyncJobGateway, request.app.state.sync_job_gateway)


def get_readiness_probe(request: Request) -> ReadinessProbe:
    """返回同时检查 PostgreSQL 与 Redis 的就绪探针。"""

    return cast(ReadinessProbe, request.app.state.readiness_probe)


def get_identity_service(request: Request) -> IdentityService:
    return cast(IdentityService, request.app.state.identity_service)


def get_seller_account_service(request: Request) -> SellerAccountService:
    service = getattr(request.app.state, "seller_account_service", None)
    if not isinstance(service, SellerAccountService):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ozon 凭据加密尚未配置",
        )
    return service


def get_session_cookie_secure(request: Request) -> bool:
    return cast(bool, getattr(request.app.state, "session_cookie_secure", False))


def get_login_rate_limiter(request: Request) -> LoginRateLimiter:
    return cast(LoginRateLimiter, request.app.state.login_rate_limiter)


def get_request_session_token(
    session: str | None = Cookie(default=None, alias="ozonslj_session"),
    authorization: str | None = Header(default=None),
) -> str | None:
    return session or _bearer_token(authorization)


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(get_request_session_token)],
) -> AuthenticatedUser:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要登录")
    user = await get_identity_service(request).authenticate(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    return user


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator and scheme.lower() == "bearer" and token:
        return token
    return None
