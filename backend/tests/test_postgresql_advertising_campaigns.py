import asyncio
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import MagicMock

from backend.app.domain.advertising_campaign import (
    AdvertisingCampaign,
    AdvertisingKeyword,
)
from backend.app.infrastructure.postgresql.advertising_campaigns import (
    PostgresAdvertisingCampaignGateway,
)
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class FakeSessions:
    def __init__(self, connection: MagicMock) -> None:
        self.connection = connection
        self.context: TenantContext | None = None

    @contextmanager
    def transaction(self, context: TenantContext) -> Any:
        self.context = context
        yield self.connection


def test_campaign_save_is_tenant_scoped_and_upserts_performance_snapshot() -> None:
    connection = MagicMock()
    sessions = FakeSessions(connection)
    context = TenantContext("org-1", "user-1")
    campaign = AdvertisingCampaign(
        campaign_id="campaign-1",
        name="Search",
        campaign_type="search",
        status="active",
        keywords=(AdvertisingKeyword("товары", 100, False),),
    )
    gateway = PostgresAdvertisingCampaignGateway(
        cast(PostgresSessionFactory, sessions), context
    )

    result = asyncio.run(gateway.save_campaigns(workspace_id="workspace-1", campaigns=[campaign]))

    assert result == [campaign]
    assert sessions.context == context
    query, params = connection.execute.call_args.args
    assert "ON CONFLICT" in query
    assert params[1:4] == ("org-1", "workspace-1", "campaign-1")
    assert "товары" in params[-1]
