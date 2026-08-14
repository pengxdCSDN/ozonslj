import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.advertising_metrics import AdvertisingMetrics
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingMetricsGateway:
    """保存带输入快照和统计窗口的广告指标，保证公式结果可回溯。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_snapshot(
        self, *, workspace_id: str, inputs: dict[str, object], metrics: AdvertisingMetrics
    ) -> AdvertisingMetrics:
        return await asyncio.to_thread(self._save, workspace_id, inputs, metrics)

    def _save(
        self, workspace_id: str, inputs: dict[str, object], metrics: AdvertisingMetrics
    ) -> AdvertisingMetrics:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO advertising_metric_snapshots
                    (id, organization_id, workspace_id, metric_window, currency,
                     inputs, metrics, complete)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    metrics.window, metrics.currency,
                    json.dumps(inputs, ensure_ascii=False),
                    json.dumps(asdict(metrics), ensure_ascii=False), metrics.complete,
                ),
            )
        return metrics

    async def list_snapshots(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingMetrics]:
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[AdvertisingMetrics]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT metrics FROM advertising_metric_snapshots
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC, id DESC LIMIT %s
                """,
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AdvertisingMetrics(**row["metrics"]) for row in rows]
