"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.cost_sensitivity import CostSensitivityScenario
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresCostSensitivityGateway:
    """保存成本敏感性场景，避免分析结果脱离原始成本假设。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_analysis(
        self,
        *,
        workspace_id: str,
        assumptions: dict[str, object],
        scenarios: tuple[CostSensitivityScenario, ...],
    ) -> tuple[CostSensitivityScenario, ...]:
        """执行 save_analysis 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    assumptions: 参数语义、输入边界和安全约束。
    scenarios: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, assumptions, scenarios)

    def _save(
        self,
        workspace_id: str,
        assumptions: dict[str, object],
        scenarios: tuple[CostSensitivityScenario, ...],
    ) -> tuple[CostSensitivityScenario, ...]:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    assumptions: 参数语义、输入边界和安全约束。
    scenarios: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO cost_sensitivity_analyses
                    (id, organization_id, workspace_id, input_assumptions, scenarios)
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    json.dumps(assumptions, ensure_ascii=False),
                    json.dumps([asdict(item) for item in scenarios], ensure_ascii=False),
                ),
            )
        return scenarios
