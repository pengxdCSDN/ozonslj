-- LST-004：保存 Search Attributes 建议、覆盖率和缺失必填属性。
BEGIN;
CREATE TABLE IF NOT EXISTS search_attributes_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    report JSONB NOT NULL,
    coverage_percent NUMERIC(6, 2) NOT NULL,
    missing_required JSONB NOT NULL,
    editable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_search_attributes_workspace_created
    ON search_attributes_reports (workspace_id, product_scope, created_at DESC);
ALTER TABLE search_attributes_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_attributes_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS search_attributes_reports_isolation ON search_attributes_reports;
CREATE POLICY search_attributes_reports_isolation ON search_attributes_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
COMMIT;
