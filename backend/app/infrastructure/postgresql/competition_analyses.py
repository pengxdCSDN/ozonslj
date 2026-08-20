"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from uuid import uuid4

from backend.app.domain.competition_analysis import CompetitionAnalysis
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresCompetitionAnalysisGateway:
    """保存公开样本竞争度推导结果，并明确估算边界。"""

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
        self, *, workspace_id: str, analysis: CompetitionAnalysis
    ) -> CompetitionAnalysis:
        """执行 save_analysis 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    analysis: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, analysis)

    def _save(self, workspace_id: str, analysis: CompetitionAnalysis) -> CompetitionAnalysis:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    analysis: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO competition_analyses
                    (id, organization_id, workspace_id, sample_count, competition_score,
                     median_price_minor, price_band_low_minor, price_band_high_minor,
                     seller_concentration_percent, brand_concentration_percent, estimated, caveat)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    analysis.sample_count, analysis.competition_score, analysis.median_price_minor,
                    analysis.price_band_low_minor, analysis.price_band_high_minor,
                    analysis.seller_concentration_percent, analysis.brand_concentration_percent,
                    analysis.estimated, analysis.caveat,
                ),
            )
        return analysis

    async def list_analyses(
        self, *, workspace_id: str, limit: int
    ) -> list[CompetitionAnalysis]:
        """执行 list_analyses 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_analyses, workspace_id, limit)

    def _list_analyses(self, workspace_id: str, limit: int) -> list[CompetitionAnalysis]:
        """执行内部步骤 _list_analyses，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT sample_count, competition_score, median_price_minor,
                    price_band_low_minor, price_band_high_minor,
                    seller_concentration_percent, brand_concentration_percent, estimated, caveat
                    FROM competition_analyses
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [CompetitionAnalysis(**row) for row in rows]
