-- Performance API 广告报表按日期保存只读事实，金额使用最小货币单位整数。
CREATE TABLE IF NOT EXISTS advertising_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    campaign_id TEXT NOT NULL,
    report_date DATE NOT NULL,
    impressions INTEGER NOT NULL CHECK (impressions >= 0),
    clicks INTEGER NOT NULL CHECK (clicks >= 0 AND clicks <= impressions),
    orders INTEGER NOT NULL CHECK (orders >= 0 AND orders <= clicks),
    sales_minor BIGINT NOT NULL CHECK (sales_minor >= 0),
    spend_minor BIGINT NOT NULL CHECK (spend_minor >= 0),
    currency TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'performance_api' CHECK (source = 'performance_api'),
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, workspace_id, campaign_id, report_date)
);
CREATE INDEX IF NOT EXISTS idx_advertising_reports_workspace_date
    ON advertising_reports (workspace_id, report_date DESC);
ALTER TABLE advertising_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertising_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS advertising_reports_isolation ON advertising_reports;
CREATE POLICY advertising_reports_isolation ON advertising_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
