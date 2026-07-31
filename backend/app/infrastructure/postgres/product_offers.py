from decimal import Decimal

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.product_offer import ProductOffer, ProductOfferPage
from backend.app.domain.store_workspace import WorkspaceNotFoundError

_MINOR_UNITS_PER_MAJOR = Decimal(100)


class PostgresProductOfferGateway:
    """从 PostgreSQL 读取工作区隔离的商品报价。"""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def list_product_offers(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> ProductOfferPage:
        start = int(cursor) if cursor is not None else 0
        async with (
            self._pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor_handle,
        ):
            await cursor_handle.execute(
                "SELECT 1 FROM store_workspaces WHERE id = %s",
                (workspace_id,),
            )
            if await cursor_handle.fetchone() is None:
                raise WorkspaceNotFoundError(workspace_id)

            await cursor_handle.execute(
                """
                    SELECT count(*) AS total
                    FROM product_offers
                    WHERE workspace_id = %s
                    """,
                (workspace_id,),
            )
            total_row = await cursor_handle.fetchone()
            total = int(total_row["total"]) if total_row is not None else 0

            await cursor_handle.execute(
                """
                    SELECT
                        offer_id,
                        ozon_product_id,
                        name,
                        price_minor,
                        currency,
                        available_stock
                    FROM product_offers
                    WHERE workspace_id = %s
                    ORDER BY position, offer_id
                    LIMIT %s OFFSET %s
                    """,
                (workspace_id, limit, start),
            )
            rows = await cursor_handle.fetchall()

        items = [
            ProductOffer(
                offer_id=str(row["offer_id"]),
                ozon_product_id=(
                    str(row["ozon_product_id"]) if row["ozon_product_id"] is not None else None
                ),
                name=str(row["name"]),
                price=Decimal(int(row["price_minor"])) / _MINOR_UNITS_PER_MAJOR,
                currency=str(row["currency"]),
                available_stock=int(row["available_stock"]),
            )
            for row in rows
        ]
        end = start + len(items)
        return ProductOfferPage(
            items=items,
            total=total,
            next_cursor=str(end) if end < total else None,
            source="postgres",
        )
