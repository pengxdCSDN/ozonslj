import asyncio
from uuid import uuid4

from backend.app.domain.competition_analysis import CompetitionAnalysis
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresCompetitionAnalysisGateway:
    """保存公开样本竞争度推导结果，并明确估算边界。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_analysis(
        self, *, workspace_id: str, analysis: CompetitionAnalysis
    ) -> CompetitionAnalysis:
        return await asyncio.to_thread(self._save, workspace_id, analysis)

    def _save(self, workspace_id: str, analysis: CompetitionAnalysis) -> CompetitionAnalysis:
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
        return await asyncio.to_thread(self._list_analyses, workspace_id, limit)

    def _list_analyses(self, workspace_id: str, limit: int) -> list[CompetitionAnalysis]:
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
