import asyncio
from uuid import uuid4

from backend.app.domain.advertising_report import AdvertisingReportRow
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingReportGateway:
    """保存按活动和日期幂等的 Performance 广告报表只读事实。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_rows(
        self, *, workspace_id: str, rows: list[AdvertisingReportRow]
    ) -> list[AdvertisingReportRow]:
        return await asyncio.to_thread(self._save, workspace_id, rows)

    def _save(
        self, workspace_id: str, rows: list[AdvertisingReportRow]
    ) -> list[AdvertisingReportRow]:
        with self._sessions.transaction(self._context) as connection:
            for row in rows:
                connection.execute(
                    """
                    INSERT INTO advertising_reports
                        (id, organization_id, workspace_id, campaign_id, report_date,
                         impressions, clicks, orders, sales_minor, spend_minor, currency)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (organization_id, workspace_id, campaign_id, report_date)
                    DO UPDATE SET impressions = EXCLUDED.impressions,
                        clicks = EXCLUDED.clicks, orders = EXCLUDED.orders,
                        sales_minor = EXCLUDED.sales_minor, spend_minor = EXCLUDED.spend_minor,
                        currency = EXCLUDED.currency, synced_at = CURRENT_TIMESTAMP
                    """,
                    (
                        str(uuid4()), self._context.organization_id, workspace_id,
                        row.campaign_id, row.report_date, row.impressions, row.clicks,
                        row.orders, row.sales_minor, row.spend_minor, row.currency,
                    ),
                )
        return rows

    async def list_rows(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingReportRow]:
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[AdvertisingReportRow]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT campaign_id, report_date, impressions, clicks, orders,
                       sales_minor, spend_minor, currency, source
                FROM advertising_reports
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY report_date DESC, synced_at DESC, id DESC LIMIT %s
                """,
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AdvertisingReportRow(**row) for row in rows]
