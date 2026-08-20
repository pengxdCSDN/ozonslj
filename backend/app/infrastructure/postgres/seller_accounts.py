"""说明本模块的职责、边界和主要协作对象。"""

from psycopg import errors
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.seller_account import (
    CreatedSellerAccount,
    SellerAccountConflictError,
)


class PostgresSellerAccountGateway:
    """原子写入卖家账号、工作区和创建者成员关系。"""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        """初始化对象依赖和运行时状态。

Args:
    pool: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._pool = pool

    async def create(
        self,
        *,
        seller_account_id: str,
        workspace_id: str,
        operator_id: str,
        display_name: str,
        workspace_name: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> CreatedSellerAccount:
        """执行 create 的业务流程并返回该流程的结果。

Args:
    seller_account_id: 参数语义、输入边界和安全约束。
    workspace_id: 参数语义、输入边界和安全约束。
    operator_id: 参数语义、输入边界和安全约束。
    display_name: 参数语义、输入边界和安全约束。
    workspace_name: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    encrypted_api_key: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    SellerAccountConflictError: 业务约束或外部依赖失败时抛出。
"""
        try:
            async with self._pool.connection() as connection, connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO seller_accounts (
                        id, display_name, ozon_client_id, encrypted_api_key,
                        credential_version, status, verified_at
                    ) VALUES (%s, %s, %s, %s, %s, 'active', now())
                    """,
                    (
                        seller_account_id,
                        display_name,
                        client_id,
                        encrypted_api_key,
                        credential_version,
                    ),
                )
                await connection.execute(
                    """
                    INSERT INTO store_workspaces (id, seller_account_id, name)
                    VALUES (%s, %s, %s)
                    """,
                    (workspace_id, seller_account_id, workspace_name),
                )
                await connection.execute(
                    """
                    INSERT INTO workspace_memberships (operator_id, workspace_id)
                    VALUES (%s, %s)
                    """,
                    (operator_id, workspace_id),
                )
        except errors.UniqueViolation as error:
            raise SellerAccountConflictError("该 Ozon Client-Id 已存在") from error
        return CreatedSellerAccount(
            seller_account_id=seller_account_id,
            workspace_id=workspace_id,
            display_name=display_name,
            workspace_name=workspace_name,
        )
