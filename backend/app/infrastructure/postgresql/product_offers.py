import asyncio
from decimal import Decimal
from typing import Any

from backend.app.domain.product_offer import ProductOffer, ProductOfferPage
from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)

_MINOR_UNITS_PER_MAJOR = Decimal(100)


class PostgresProductOfferGateway:
    """读取 PostgreSQL 中按组织与工作区隔离的商品报价事实。"""

    def __init__(
        self,
        sessions: PostgresSessionFactory,
        tenant_context: TenantContext,
    ) -> None:
        self._sessions = sessions
        self._tenant_context = tenant_context

    async def list_product_offers(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> ProductOfferPage:
        return await asyncio.to_thread(
            self._list_product_offers,
            workspace_id,
            int(cursor) if cursor is not None else 0,
            limit,
        )

    def _list_product_offers(
        self,
        workspace_id: str,
        offset: int,
        limit: int,
    ) -> ProductOfferPage:
        with self._sessions.transaction(self._tenant_context) as connection:
            count_row = connection.execute(
                """
                SELECT count(*) AS total
                FROM product_offers
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._tenant_context.organization_id, workspace_id),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT offer_id, ozon_product_id, name, price_minor,
                       currency, available_stock
                FROM product_offers
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY position
                LIMIT %s OFFSET %s
                """,
                (
                    self._tenant_context.organization_id,
                    workspace_id,
                    limit,
                    offset,
                ),
            ).fetchall()

        total = int(count_row["total"]) if count_row is not None else 0
        items = [_product_offer_from_row(row) for row in rows]
        end = offset + len(items)
        return ProductOfferPage(
            items=items,
            total=total,
            next_cursor=str(end) if end < total else None,
            source="postgresql",
        )


def _product_offer_from_row(row: dict[str, Any]) -> ProductOffer:
    """把最小货币单位整数转换为 API 使用的精确 Decimal。"""
    return ProductOffer(
        offer_id=str(row["offer_id"]),
        ozon_product_id=(
            str(row["ozon_product_id"])
            if row["ozon_product_id"] is not None
            else None
        ),
        name=str(row["name"]),
        price=Decimal(int(row["price_minor"])) / _MINOR_UNITS_PER_MAJOR,
        currency=str(row["currency"]),
        available_stock=int(row["available_stock"]),
    )
