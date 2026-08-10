-- 保存销售分析、异常和机会建议快照，供日报和复盘复用。
CREATE TABLE IF NOT EXISTS sales_analysis_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    report JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sales_analysis_workspace_created
    ON sales_analysis_reports (workspace_id, created_at DESC);
ALTER TABLE sales_analysis_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_analysis_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sales_analysis_isolation ON sales_analysis_reports;
CREATE POLICY sales_analysis_isolation ON sales_analysis_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
