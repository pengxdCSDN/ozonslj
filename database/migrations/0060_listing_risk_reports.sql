-- 保存 Listing 风险标记和原始文本，供人工修改、审核和版本管理复用。
CREATE TABLE IF NOT EXISTS listing_risk_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    original_text TEXT NOT NULL,
    findings JSONB NOT NULL,
    safe_to_review BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_listing_risk_reports_workspace_created
    ON listing_risk_reports (workspace_id, product_scope, created_at DESC);
ALTER TABLE listing_risk_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_risk_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_risk_reports_isolation ON listing_risk_reports;
CREATE POLICY listing_risk_reports_isolation ON listing_risk_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
