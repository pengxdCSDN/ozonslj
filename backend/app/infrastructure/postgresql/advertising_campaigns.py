import asyncio
import json
from uuid import uuid4

from backend.app.domain.advertising_campaign import (
    AdvertisingCampaign,
    AdvertisingKeyword,
)
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingCampaignGateway:
    """保存 Performance 广告活动只读快照，并按组织和工作区查询历史状态。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_campaigns(
        self, *, workspace_id: str, campaigns: list[AdvertisingCampaign]
    ) -> list[AdvertisingCampaign]:
        return await asyncio.to_thread(self._save, workspace_id, campaigns)

    def _save(
        self, workspace_id: str, campaigns: list[AdvertisingCampaign]
    ) -> list[AdvertisingCampaign]:
        with self._sessions.transaction(self._context) as connection:
            for campaign in campaigns:
                keywords = [
                    {
                        "keyword": item.keyword,
                        "bid_minor": item.bid_minor,
                        "negative": item.negative,
                    }
                    for item in campaign.keywords
                ]
                connection.execute(
                    """
                    INSERT INTO advertising_campaigns
                        (id, organization_id, workspace_id, campaign_id, name,
                         campaign_type, status, keywords, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'performance_api')
                    ON CONFLICT (organization_id, workspace_id, campaign_id) DO UPDATE SET
                        name = EXCLUDED.name, campaign_type = EXCLUDED.campaign_type,
                        status = EXCLUDED.status, keywords = EXCLUDED.keywords,
                        source = EXCLUDED.source, synced_at = CURRENT_TIMESTAMP
                    """,
                    (
                        str(uuid4()), self._context.organization_id, workspace_id,
                        campaign.campaign_id, campaign.name, campaign.campaign_type,
                        campaign.status, json.dumps(keywords, ensure_ascii=False),
                    ),
                )
        return campaigns

    async def list_campaigns(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingCampaign]:
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[AdvertisingCampaign]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT campaign_id, name, campaign_type, status, keywords, source
                FROM advertising_campaigns
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY synced_at DESC, id DESC LIMIT %s
                """,
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [
            AdvertisingCampaign(
                campaign_id=row["campaign_id"], name=row["name"],
                campaign_type=row["campaign_type"], status=row["status"],
                keywords=tuple(AdvertisingKeyword(**item) for item in row["keywords"]),
                source=row["source"],
            )
            for row in rows
        ]
