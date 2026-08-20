"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.profit_model import ProfitScenario
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresProfitModelGateway:
    """保存利润输入假设和 FBO/FBS 结果，供后续敏感性分析回溯。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save_model(
        self,
        *,
        workspace_id: str,
        assumptions: dict[str, object],
        scenarios: tuple[ProfitScenario, ProfitScenario],
    ) -> tuple[ProfitScenario, ProfitScenario]:
        """执行 save_model 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, assumptions, scenarios)

    def _save(
        self,
        workspace_id: str,
        assumptions: dict[str, object],
        scenarios: tuple[ProfitScenario, ProfitScenario],
    ) -> tuple[ProfitScenario, ProfitScenario]:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            version_row = connection.execute(
                """
                SELECT COALESCE(MAX(assumption_version), 0) + 1 AS next_version
                FROM profit_models
                WHERE organization_id = %s AND workspace_id = %s
                """,
                (self._context.organization_id, workspace_id),
            ).fetchone()
            version = int(version_row["next_version"]) if version_row is not None else 1
            connection.execute(
                """
                INSERT INTO profit_models
                    (id, organization_id, workspace_id, assumption_version,
                     input_assumptions, fbo_result, fbs_result)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, version,
                    json.dumps(assumptions, ensure_ascii=False),
                    json.dumps(asdict(scenarios[0]), ensure_ascii=False),
                    json.dumps(asdict(scenarios[1]), ensure_ascii=False),
                ),
            )
        return scenarios
