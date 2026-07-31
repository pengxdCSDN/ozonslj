from typing import Protocol, cast

from fastapi import Request

from backend.app.domain.store_workspace import StoreWorkspaceGateway
from backend.app.infrastructure.ozon.gateway import ProductOfferGateway


class ReadinessProbe(Protocol):
    """定义 API 就绪检查所需的最小依赖能力。"""

    async def check(self) -> None: ...


def get_product_offer_gateway(request: Request) -> ProductOfferGateway:
    """从应用生命周期状态获取 PostgreSQL 商品仓储。"""

    return cast(ProductOfferGateway, request.app.state.product_offer_gateway)


def get_store_workspace_gateway(request: Request) -> StoreWorkspaceGateway:
    """从应用生命周期状态获取 PostgreSQL 工作区仓储。"""

    return cast(StoreWorkspaceGateway, request.app.state.store_workspace_gateway)


def get_readiness_probe(request: Request) -> ReadinessProbe:
    """返回同时检查 PostgreSQL 与 Redis 的就绪探针。"""

    return cast(ReadinessProbe, request.app.state.readiness_probe)
