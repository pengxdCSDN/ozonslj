-- FABE 草稿保存特性、优势、利益、证据和图片文案建议，保留证据缺失提示。
CREATE TABLE IF NOT EXISTS listing_fabe_drafts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    bullets JSONB NOT NULL,
    long_description TEXT NOT NULL,
    image_copy_suggestions JSONB NOT NULL,
    missing_evidence JSONB NOT NULL,
    editable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_listing_fabe_drafts_workspace_created
    ON listing_fabe_drafts (workspace_id, product_scope, created_at DESC);
ALTER TABLE listing_fabe_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_fabe_drafts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_fabe_drafts_isolation ON listing_fabe_drafts;
CREATE POLICY listing_fabe_drafts_isolation ON listing_fabe_drafts
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
