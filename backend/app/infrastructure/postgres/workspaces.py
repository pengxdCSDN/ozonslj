from typing import cast

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.store_workspace import SellerAccountStatus, StoreWorkspace


class PostgresStoreWorkspaceGateway:
    """从 PostgreSQL 返回不含任何卖家凭据的工作区目录。"""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def list_store_workspaces(self) -> list[StoreWorkspace]:
        async with (
            self._pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                """
                    SELECT
                        workspaces.id,
                        workspaces.name,
                        accounts.display_name AS seller_display_name,
                        accounts.status AS seller_status
                    FROM store_workspaces AS workspaces
                    JOIN seller_accounts AS accounts
                      ON accounts.id = workspaces.seller_account_id
                    ORDER BY workspaces.created_at, workspaces.id
                    """
            )
            rows = await cursor.fetchall()
        return [
            StoreWorkspace(
                id=str(row["id"]),
                name=str(row["name"]),
                seller_display_name=str(row["seller_display_name"]),
                seller_status=cast(SellerAccountStatus, str(row["seller_status"])),
            )
            for row in rows
        ]
