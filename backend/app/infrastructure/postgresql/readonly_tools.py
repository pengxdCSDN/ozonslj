"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from uuid import uuid4

from backend.app.domain.readonly_tool import ReadonlyToolDecision
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresReadonlyToolGateway:
    """记录只读工具授权结果，便于审计参数过滤和 SQL/写入阻断。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_decision(
        self, *, workspace_id: str, decision: ReadonlyToolDecision
    ) -> ReadonlyToolDecision:
        """执行 save_decision 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, decision)

    def _save(
        self, workspace_id: str, decision: ReadonlyToolDecision
    ) -> ReadonlyToolDecision:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO readonly_tool_authorizations
                    (id, organization_id, workspace_id, tool, allowed, parameters,
                     reason, sql_allowed)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    decision.tool, decision.allowed, json.dumps(decision.parameters),
                    decision.reason, decision.sql_allowed,
                ),
            )
        return decision

    async def list_decisions(
        self, *, workspace_id: str, limit: int
    ) -> list[ReadonlyToolDecision]:
        """执行 list_decisions 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_decisions, workspace_id, limit)

    def _list_decisions(self, workspace_id: str, limit: int) -> list[ReadonlyToolDecision]:
        """执行内部步骤 _list_decisions，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT tool, allowed, parameters, reason, sql_allowed
                    FROM readonly_tool_authorizations
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [ReadonlyToolDecision(
            tool=str(row["tool"]), allowed=bool(row["allowed"]),
            parameters={str(key): str(value) for key, value in row["parameters"].items()},
            reason=str(row["reason"]), sql_allowed=bool(row["sql_allowed"]),
        ) for row in rows]
