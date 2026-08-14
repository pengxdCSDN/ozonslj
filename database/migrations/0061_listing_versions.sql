-- 保存 Listing 原文、人工修改、差异和审核状态；未审核版本不得进入发布链路。
CREATE TABLE IF NOT EXISTS listing_versions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    original_text TEXT NOT NULL,
    edited_text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'review', 'approved', 'rejected')),
    diff JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, product_scope, version_no)
);
CREATE INDEX IF NOT EXISTS idx_listing_versions_workspace_created
    ON listing_versions (workspace_id, product_scope, created_at DESC);
ALTER TABLE listing_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_versions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_versions_isolation ON listing_versions;
CREATE POLICY listing_versions_isolation ON listing_versions
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
