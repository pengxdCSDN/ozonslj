"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from psycopg import Connection
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from backend.app.domain.store_workspace import (
    ClientIdConflictError,
    StoreWorkspace,
    StoreWorkspaceStatus,
)
from backend.app.infrastructure.postgresql.session import (
    PostgresSessionFactory,
    TenantContext,
)


class PostgresStoreWorkspaceGateway:
    """在 PostgreSQL 单事务内维护当前组织的卖家账户与工作区聚合。"""

    def __init__(
        self,
        sessions: PostgresSessionFactory,
        tenant_context: TenantContext,
    ) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    tenant_context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._tenant_context = tenant_context

    async def list_workspaces(self) -> list[StoreWorkspace]:
        """执行 list_workspaces 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_workspaces)

    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        """执行 get_workspace 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._get_workspace, workspace_id)

    async def create_workspace(
        self,
        *,
        display_name: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> StoreWorkspace:
        """执行 create_workspace 的业务流程并返回该流程的结果。

Args:
    display_name: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    encrypted_api_key: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._create_workspace,
            display_name.strip(),
            client_id.strip(),
            encrypted_api_key,
            credential_version,
        )

    async def replace_credentials(
        self,
        *,
        workspace_id: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> StoreWorkspace | None:
        """执行 replace_credentials 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    encrypted_api_key: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._replace_credentials,
            workspace_id,
            client_id.strip(),
            encrypted_api_key,
            credential_version,
        )

    async def load_credentials(self, workspace_id: str) -> tuple[str, bytes, int] | None:
        """执行 load_credentials 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._load_credentials, workspace_id)

    async def set_verification_status(
        self,
        *,
        workspace_id: str,
        status: StoreWorkspaceStatus,
        verified_at: datetime | None,
        audit_result: Literal["success", "failed"],
        audit_detail: dict[str, str] | None = None,
    ) -> StoreWorkspace | None:
        """执行 set_verification_status 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。
    verified_at: 参数语义、输入边界和安全约束。
    audit_result: 参数语义、输入边界和安全约束。
    audit_detail: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._set_verification_status,
            workspace_id,
            status,
            verified_at,
            audit_result,
            audit_detail,
        )

    def _list_workspaces(self) -> list[StoreWorkspace]:
        """执行内部步骤 _list_workspaces，供同一模块的公开流程复用。
Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._tenant_context) as connection:
            rows = connection.execute(
                f"{_WORKSPACE_SELECT} ORDER BY w.created_at, w.id",
                (self._tenant_context.organization_id,),
            ).fetchall()
        return [_workspace_from_row(row) for row in rows]

    def _get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        """执行内部步骤 _get_workspace，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._tenant_context) as connection:
            row = connection.execute(
                f"{_WORKSPACE_SELECT} AND w.id = %s",
                (self._tenant_context.organization_id, workspace_id),
            ).fetchone()
        return _workspace_from_row(row) if row is not None else None

    def _create_workspace(
        self,
        display_name: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> StoreWorkspace:
        """执行内部步骤 _create_workspace，供同一模块的公开流程复用。

Args:
    display_name: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    encrypted_api_key: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    RuntimeError: 业务约束或外部依赖失败时抛出。
    ClientIdConflictError: 业务约束或外部依赖失败时抛出。
"""
        seller_id = str(uuid4())
        workspace_id = str(uuid4())
        try:
            with self._sessions.transaction(self._tenant_context) as connection:
                connection.execute(
                    """
                    INSERT INTO seller_accounts (
                        id, organization_id, display_name, ozon_client_id,
                        encrypted_api_key, credential_version, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                    """,
                    (
                        seller_id,
                        self._tenant_context.organization_id,
                        display_name,
                        client_id,
                        encrypted_api_key,
                        credential_version,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO store_workspaces (
                        id, organization_id, seller_account_id, name
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (
                        workspace_id,
                        self._tenant_context.organization_id,
                        seller_id,
                        display_name,
                    ),
                )
                _insert_audit(
                    connection,
                    context=self._tenant_context,
                    workspace_id=workspace_id,
                    operation_type="workspace.create",
                    risk_level="reversible_write",
                    result="success",
                    detail={"status": "pending"},
                )
        except UniqueViolation as error:
            if error.diag.constraint_name == "uq_seller_accounts_org_client":
                raise ClientIdConflictError("Client ID 已存在") from error
            raise
        workspace = self._get_workspace(workspace_id)
        if workspace is None:
            raise RuntimeError("创建工作区后无法在当前租户中重新读取")
        return workspace

    def _replace_credentials(
        self,
        workspace_id: str,
        client_id: str,
        encrypted_api_key: bytes,
        credential_version: int,
    ) -> StoreWorkspace | None:
        """执行内部步骤 _replace_credentials，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    client_id: 参数语义、输入边界和安全约束。
    encrypted_api_key: 参数语义、输入边界和安全约束。
    credential_version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ClientIdConflictError: 业务约束或外部依赖失败时抛出。
"""
        try:
            with self._sessions.transaction(self._tenant_context) as connection:
                cursor = connection.execute(
                    """
                    UPDATE seller_accounts AS account
                    SET ozon_client_id = %s,
                        encrypted_api_key = %s,
                        credential_version = %s,
                        status = 'pending',
                        verified_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    FROM store_workspaces AS workspace
                    WHERE workspace.id = %s
                      AND workspace.organization_id = %s
                      AND account.id = workspace.seller_account_id
                      AND account.organization_id = workspace.organization_id
                    """,
                    (
                        client_id,
                        encrypted_api_key,
                        credential_version,
                        workspace_id,
                        self._tenant_context.organization_id,
                    ),
                )
                if cursor.rowcount == 0:
                    return None
                _insert_audit(
                    connection,
                    context=self._tenant_context,
                    workspace_id=workspace_id,
                    operation_type="credentials.replace",
                    risk_level="reversible_write",
                    result="success",
                    detail={"status": "pending"},
                )
        except UniqueViolation as error:
            if error.diag.constraint_name == "uq_seller_accounts_org_client":
                raise ClientIdConflictError("Client ID 已存在") from error
            raise
        return self._get_workspace(workspace_id)

    def _load_credentials(self, workspace_id: str) -> tuple[str, bytes, int] | None:
        """执行内部步骤 _load_credentials，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._tenant_context) as connection:
            row = connection.execute(
                """
                SELECT account.ozon_client_id, account.encrypted_api_key,
                       account.credential_version
                FROM store_workspaces AS workspace
                JOIN seller_accounts AS account
                  ON account.organization_id = workspace.organization_id
                 AND account.id = workspace.seller_account_id
                WHERE workspace.organization_id = %s AND workspace.id = %s
                """,
                (self._tenant_context.organization_id, workspace_id),
            ).fetchone()
        if row is None:
            return None
        return (
            str(row["ozon_client_id"]),
            bytes(row["encrypted_api_key"]),
            int(row["credential_version"]),
        )

    def _set_verification_status(
        self,
        workspace_id: str,
        status: StoreWorkspaceStatus,
        verified_at: datetime | None,
        audit_result: Literal["success", "failed"],
        audit_detail: dict[str, str] | None,
    ) -> StoreWorkspace | None:
        """执行内部步骤 _set_verification_status，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。
    verified_at: 参数语义、输入边界和安全约束。
    audit_result: 参数语义、输入边界和安全约束。
    audit_detail: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._tenant_context) as connection:
            cursor = connection.execute(
                """
                UPDATE seller_accounts AS account
                SET status = %s, verified_at = %s, updated_at = CURRENT_TIMESTAMP
                FROM store_workspaces AS workspace
                WHERE workspace.id = %s
                  AND workspace.organization_id = %s
                  AND account.id = workspace.seller_account_id
                  AND account.organization_id = workspace.organization_id
                """,
                (
                    status,
                    verified_at,
                    workspace_id,
                    self._tenant_context.organization_id,
                ),
            )
            if cursor.rowcount == 0:
                return None
            _insert_audit(
                connection,
                context=self._tenant_context,
                workspace_id=workspace_id,
                operation_type="credentials.verify",
                risk_level="read",
                result=audit_result,
                detail=audit_detail,
            )
        return self._get_workspace(workspace_id)


_WORKSPACE_SELECT = """
SELECT
    w.id,
    w.name AS display_name,
    a.status,
    a.verified_at,
    w.created_at,
    a.updated_at
FROM store_workspaces AS w
JOIN seller_accounts AS a
  ON a.organization_id = w.organization_id
 AND a.id = w.seller_account_id
WHERE w.organization_id = %s
"""


def _workspace_from_row(row: dict[str, Any]) -> StoreWorkspace:
    """执行内部步骤 _workspace_from_row，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return StoreWorkspace.model_validate(row)


def _insert_audit(
    connection: Connection[dict[str, Any]],
    *,
    context: TenantContext,
    workspace_id: str,
    operation_type: str,
    risk_level: Literal["read", "reversible_write"],
    result: Literal["success", "failed"],
    detail: dict[str, str] | None,
) -> None:
    """写入脱敏审计；调用方必须与业务变更共享同一数据库事务。

Args:
    connection: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。
    workspace_id: 参数语义、输入边界和安全约束。
    operation_type: 参数语义、输入边界和安全约束。
    risk_level: 参数语义、输入边界和安全约束。
    result: 参数语义、输入边界和安全约束。
    detail: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    connection.execute(
        """
        INSERT INTO seller_operations (
            id, organization_id, workspace_id, user_id, operation_type,
            risk_level, target_type, target_count, result, detail_json
        ) VALUES (%s, %s, %s, %s, %s, %s, 'seller_account', 1, %s, %s)
        """,
        (
            str(uuid4()),
            context.organization_id,
            workspace_id,
            context.user_id,
            operation_type,
            risk_level,
            result,
            Jsonb(detail) if detail is not None else None,
        ),
    )
