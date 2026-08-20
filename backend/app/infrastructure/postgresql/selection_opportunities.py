"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from uuid import uuid4

from backend.app.domain.selection_explore import ExploreOpportunity
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresExploreOpportunityGateway:
    """保存 Explore 结果快照，保留评分原因和估算边界。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_opportunities(
        self, *, workspace_id: str, opportunities: list[ExploreOpportunity]
    ) -> list[ExploreOpportunity]:
        """执行 save_opportunities 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    opportunities: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, opportunities)

    def _save(
        self, workspace_id: str, opportunities: list[ExploreOpportunity]
    ) -> list[ExploreOpportunity]:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    opportunities: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            for item in opportunities:
                connection.execute(
                    """
                    INSERT INTO selection_opportunities
                        (id, organization_id, workspace_id, keyword, score, search_count,
                         sample_count, conversion_rate, median_price_minor, own_coverage_gap,
                         estimated, reasons)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        str(uuid4()), self._context.organization_id, workspace_id, item.keyword,
                        item.score, item.search_count, item.sample_count, item.conversion_rate,
                        item.median_price_minor, item.own_coverage_gap, item.estimated,
                        json.dumps(item.reasons, ensure_ascii=False),
                    ),
                )
        return opportunities

    async def list_opportunities(
        self, *, workspace_id: str, limit: int
    ) -> list[ExploreOpportunity]:
        """执行 list_opportunities 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_opportunities, workspace_id, limit)

    def _list_opportunities(self, workspace_id: str, limit: int) -> list[ExploreOpportunity]:
        """执行内部步骤 _list_opportunities，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT keyword, score, search_count, conversion_rate, sample_count,
                    median_price_minor, own_coverage_gap, estimated, reasons
                    FROM selection_opportunities
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, score DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [ExploreOpportunity(
            keyword=str(row["keyword"]), score=float(row["score"]),
            search_count=int(row["search_count"]), conversion_rate=row["conversion_rate"],
            sample_count=int(row["sample_count"]), median_price_minor=row["median_price_minor"],
            own_coverage_gap=bool(row["own_coverage_gap"]), estimated=bool(row["estimated"]),
            reasons=tuple(str(value) for value in row["reasons"]), missing_inputs=(),
        ) for row in rows]
