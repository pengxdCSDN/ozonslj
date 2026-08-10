-- Listing 版本保留原稿、人工修改稿、差异和审核状态，版本不得覆盖历史内容。
CREATE TABLE IF NOT EXISTS listing_versions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    original_text TEXT NOT NULL,
    edited_text TEXT NOT NULL,
    diff JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'review', 'approved', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, workspace_id, product_scope, version)
);
CREATE INDEX IF NOT EXISTS idx_listing_versions_workspace_product
    ON listing_versions (workspace_id, product_scope, version DESC);
ALTER TABLE listing_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_versions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_versions_isolation ON listing_versions;
CREATE POLICY listing_versions_isolation ON listing_versions
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
