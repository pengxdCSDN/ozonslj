-- 广告诊断阈值按工作区版本化保存，避免历史诊断失去当时的判定口径。
CREATE TABLE IF NOT EXISTS advertising_threshold_versions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    min_impressions INTEGER NOT NULL CHECK (min_impressions >= 0),
    min_clicks INTEGER NOT NULL CHECK (min_clicks >= 0),
    high_cvr_percent NUMERIC NOT NULL CHECK (high_cvr_percent >= 0),
    high_spend_minor BIGINT NOT NULL CHECK (high_spend_minor >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, version_no)
);
CREATE INDEX IF NOT EXISTS idx_ad_threshold_workspace_created
    ON advertising_threshold_versions (workspace_id, created_at DESC);
ALTER TABLE advertising_threshold_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertising_threshold_versions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ad_threshold_isolation ON advertising_threshold_versions;
CREATE POLICY ad_threshold_isolation ON advertising_threshold_versions
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
