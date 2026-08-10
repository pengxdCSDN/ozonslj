-- 保存新品广告 30 天建议日历快照，便于复盘当时的阶段和建议口径。
CREATE TABLE IF NOT EXISTS advertising_calendars (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    days JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ad_calendars_workspace_created
    ON advertising_calendars (workspace_id, start_date DESC, created_at DESC);
ALTER TABLE advertising_calendars ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertising_calendars FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ad_calendars_isolation ON advertising_calendars;
CREATE POLICY ad_calendars_isolation ON advertising_calendars
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
