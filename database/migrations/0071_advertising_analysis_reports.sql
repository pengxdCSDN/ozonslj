-- 保存 ACOS/TACOS/ROI、异常和预算建议快照。
CREATE TABLE IF NOT EXISTS advertising_analysis_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    report JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ad_analysis_workspace_created
    ON advertising_analysis_reports (workspace_id, created_at DESC);
ALTER TABLE advertising_analysis_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertising_analysis_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ad_analysis_isolation ON advertising_analysis_reports;
CREATE POLICY ad_analysis_isolation ON advertising_analysis_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
