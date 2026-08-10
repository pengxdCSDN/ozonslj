-- 关键词分层结果保存规则原因和人工确认标记，避免自动分类覆盖人工判断。
CREATE TABLE IF NOT EXISTS listing_keyword_layers (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    layer TEXT NOT NULL CHECK (layer IN ('core', 'attribute', 'scene', 'long_tail')),
    reason TEXT NOT NULL,
    manually_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_listing_keyword_layers_workspace_layer
    ON listing_keyword_layers (workspace_id, layer, created_at DESC);
ALTER TABLE listing_keyword_layers ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_keyword_layers FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_keyword_layers_isolation ON listing_keyword_layers;
CREATE POLICY listing_keyword_layers_isolation ON listing_keyword_layers
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
