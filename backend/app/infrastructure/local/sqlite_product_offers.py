import asyncio
import sqlite3
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

from backend.app.domain.product_offer import ProductOffer, ProductOfferPage


class SqliteProductOfferGateway:
    """Persist the local Product Offer cache in a single SQLite file."""

    def __init__(self, database_path: Path, seed_offers: Sequence[ProductOffer]) -> None:
        self._database_path = database_path
        self._seed_offers = seed_offers

    async def list_product_offers(
        self,
        *,
        cursor: str | None,
        limit: int,
    ) -> ProductOfferPage:
        return await asyncio.to_thread(self._list_product_offers, cursor, limit)

    def _list_product_offers(self, cursor: str | None, limit: int) -> ProductOfferPage:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS product_offers (
                    position INTEGER NOT NULL,
                    offer_id TEXT PRIMARY KEY,
                    ozon_product_id TEXT,
                    name TEXT NOT NULL,
                    price TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    available_stock INTEGER NOT NULL
                )
                """
            )
            self._seed_if_empty(connection)
            total = int(
                connection.execute("SELECT COUNT(*) FROM product_offers").fetchone()[0]
            )
            start = int(cursor) if cursor else 0
            rows = connection.execute(
                """
                SELECT offer_id, ozon_product_id, name, price, currency, available_stock
                FROM product_offers
                ORDER BY position
                LIMIT ? OFFSET ?
                """,
                (limit, start),
            ).fetchall()

        items = [
            ProductOffer(
                offer_id=row[0],
                ozon_product_id=row[1],
                name=row[2],
                price=Decimal(row[3]),
                currency=row[4],
                available_stock=row[5],
            )
            for row in rows
        ]
        end = start + len(items)
        return ProductOfferPage(
            items=items,
            total=total,
            next_cursor=str(end) if end < total else None,
            source="sqlite",
        )

    def _seed_if_empty(self, connection: sqlite3.Connection) -> None:
        if connection.execute("SELECT 1 FROM product_offers LIMIT 1").fetchone():
            return
        connection.executemany(
            """
            INSERT INTO product_offers (
                position, offer_id, ozon_product_id, name, price, currency, available_stock
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    position,
                    offer.offer_id,
                    offer.ozon_product_id,
                    offer.name,
                    str(offer.price),
                    offer.currency,
                    offer.available_stock,
                )
                for position, offer in enumerate(self._seed_offers)
            ],
        )
