-- Search Attributes 报告保存建议值、来源和覆盖率，草稿不会自动写入商品。
CREATE TABLE IF NOT EXISTS search_attribute_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    suggestions JSONB NOT NULL,
    coverage_percent NUMERIC(6, 2) NOT NULL,
    missing_required JSONB NOT NULL,
    editable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_search_attribute_reports_workspace_created
    ON search_attribute_reports (workspace_id, product_scope, created_at DESC);
ALTER TABLE search_attribute_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_attribute_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS search_attribute_reports_isolation ON search_attribute_reports;
CREATE POLICY search_attribute_reports_isolation ON search_attribute_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
