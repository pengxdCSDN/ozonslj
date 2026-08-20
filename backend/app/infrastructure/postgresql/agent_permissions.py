"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.agent_permissions import AgentPermissionDecision
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAgentPermissionGateway:
    """保存 Agent 权限判定；权限硬编码为只读，不接受提示词覆盖。"""

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
        self, *, workspace_id: str, decision: AgentPermissionDecision
    ) -> AgentPermissionDecision:
        """执行 save_decision 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, decision)

    def _save(
        self, workspace_id: str, decision: AgentPermissionDecision
    ) -> AgentPermissionDecision:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO agent_permission_checks
                    (id, organization_id, workspace_id, agent, decision)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    decision.agent, json.dumps(asdict(decision), ensure_ascii=False),
                ),
            )
        return decision

    async def list_decisions(
        self, *, workspace_id: str, limit: int
    ) -> list[AgentPermissionDecision]:
        """执行 list_decisions 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_decisions, workspace_id, limit)

    def _list_decisions(self, workspace_id: str, limit: int) -> list[AgentPermissionDecision]:
        """执行内部步骤 _list_decisions，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT decision FROM agent_permission_checks
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AgentPermissionDecision(**row["decision"]) for row in rows]
