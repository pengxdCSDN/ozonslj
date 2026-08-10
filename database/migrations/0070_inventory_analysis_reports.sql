-- 保存库存覆盖、缺货/积压风险和补货建议快照。
CREATE TABLE IF NOT EXISTS inventory_analysis_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    report JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_inventory_analysis_workspace_created
    ON inventory_analysis_reports (workspace_id, created_at DESC);
ALTER TABLE inventory_analysis_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_analysis_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS inventory_analysis_isolation ON inventory_analysis_reports;
CREATE POLICY inventory_analysis_isolation ON inventory_analysis_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
