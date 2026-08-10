-- 标题仅保存可编辑草稿和覆盖报告，不直接修改 Ozon 商品。
CREATE TABLE IF NOT EXISTS listing_title_drafts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    covered_terms JSONB NOT NULL,
    missing_terms JSONB NOT NULL,
    character_count INTEGER NOT NULL,
    risks JSONB NOT NULL,
    editable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_listing_title_drafts_workspace_created
    ON listing_title_drafts (workspace_id, product_scope, created_at DESC);
ALTER TABLE listing_title_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_title_drafts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_title_drafts_isolation ON listing_title_drafts;
CREATE POLICY listing_title_drafts_isolation ON listing_title_drafts
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
