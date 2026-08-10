-- 保存日报、周报、月报和站内待办汇总快照。
CREATE TABLE IF NOT EXISTS summary_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL CHECK (report_type IN ('daily', 'weekly', 'monthly')),
    period TEXT NOT NULL,
    report JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_summary_reports_workspace_created
    ON summary_reports (workspace_id, report_type, period, created_at DESC);
ALTER TABLE summary_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE summary_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS summary_reports_isolation ON summary_reports;
CREATE POLICY summary_reports_isolation ON summary_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
