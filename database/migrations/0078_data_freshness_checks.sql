-- 保存差异预览和受控执行前的数据新鲜度判定。
CREATE TABLE IF NOT EXISTS data_freshness_checks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    data_domain TEXT NOT NULL,
    decision JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_data_freshness_workspace_created
    ON data_freshness_checks (workspace_id, data_domain, created_at DESC);
ALTER TABLE data_freshness_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_freshness_checks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS data_freshness_isolation ON data_freshness_checks;
CREATE POLICY data_freshness_isolation ON data_freshness_checks
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
