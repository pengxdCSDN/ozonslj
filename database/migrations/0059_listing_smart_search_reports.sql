-- 保存 Smart Search 检查结果与原文快照，便于人工复核和版本追踪。
CREATE TABLE IF NOT EXISTS listing_smart_search_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    source_text TEXT NOT NULL,
    findings JSONB NOT NULL,
    covered_terms JSONB NOT NULL,
    missing_terms JSONB NOT NULL,
    valid BOOLEAN NOT NULL,
    original_text_preserved BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_listing_smart_search_workspace_created
    ON listing_smart_search_reports (workspace_id, product_scope, created_at DESC);
ALTER TABLE listing_smart_search_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_smart_search_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_smart_search_isolation ON listing_smart_search_reports;
CREATE POLICY listing_smart_search_isolation ON listing_smart_search_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
