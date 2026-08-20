"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from uuid import uuid4

from backend.app.domain.advertising_readonly import AdvertisingReadOnlyDecision
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingBoundaryGateway:
    """记录广告动作边界判定，确保被阻断的写动作也可审计。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_check(
        self, *, workspace_id: str, decision: AdvertisingReadOnlyDecision
    ) -> AdvertisingReadOnlyDecision:
        """执行 save_check 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, decision)

    def _save(
        self, workspace_id: str, decision: AdvertisingReadOnlyDecision
    ) -> AdvertisingReadOnlyDecision:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO advertising_boundary_checks
                    (id, organization_id, workspace_id, action, allowed, reason, audit_required)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    decision.action, decision.allowed, decision.reason, decision.audit_required,
                ),
            )
        return decision

    async def list_checks(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingReadOnlyDecision]:
        """执行 list_checks 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_checks, workspace_id, limit)

    def _list_checks(self, workspace_id: str, limit: int) -> list[AdvertisingReadOnlyDecision]:
        """执行内部步骤 _list_checks，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT action, allowed, reason, audit_required
                    FROM advertising_boundary_checks
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AdvertisingReadOnlyDecision(
            action=str(row["action"]), allowed=bool(row["allowed"]),
            reason=str(row["reason"]), audit_required=bool(row["audit_required"]),
        ) for row in rows]
