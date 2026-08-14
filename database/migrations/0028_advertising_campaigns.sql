-- 广告活动、关键词和否定词为 Performance API 只读事实快照，不允许前端直接写回。
CREATE TABLE IF NOT EXISTS advertising_campaigns (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    campaign_id TEXT NOT NULL,
    name TEXT NOT NULL,
    campaign_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'paused', 'archived')),
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    source TEXT NOT NULL DEFAULT 'performance_api' CHECK (source = 'performance_api'),
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, workspace_id, campaign_id)
);
CREATE INDEX IF NOT EXISTS idx_advertising_campaigns_workspace_status
    ON advertising_campaigns (workspace_id, status, synced_at DESC);
ALTER TABLE advertising_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertising_campaigns FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS advertising_campaigns_isolation ON advertising_campaigns;
CREATE POLICY advertising_campaigns_isolation ON advertising_campaigns
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
