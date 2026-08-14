-- 保存竞品样本与选品机会综合分析，并保留采样估算边界。
CREATE TABLE IF NOT EXISTS competitor_selection_analysis_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    report JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_competitor_selection_workspace_created
    ON competitor_selection_analysis_reports (workspace_id, created_at DESC);
ALTER TABLE competitor_selection_analysis_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_selection_analysis_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS competitor_selection_isolation ON competitor_selection_analysis_reports;
CREATE POLICY competitor_selection_isolation ON competitor_selection_analysis_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
