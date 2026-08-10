-- Listing 关键词必须保留来源、统计时间、语言、分层和适用商品范围。
CREATE TABLE IF NOT EXISTS listing_keywords (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    source TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    language TEXT NOT NULL,
    layer TEXT NOT NULL CHECK (layer IN ('core', 'attribute', 'scene', 'long_tail')),
    product_scope TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_listing_keywords_workspace_layer
    ON listing_keywords (workspace_id, product_scope, layer, observed_at DESC);
ALTER TABLE listing_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_keywords FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_keywords_isolation ON listing_keywords;
CREATE POLICY listing_keywords_isolation ON listing_keywords
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
