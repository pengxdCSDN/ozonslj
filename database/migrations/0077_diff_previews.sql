-- 保存写入前旧值、新值、来源、影响及人工复核标记。
CREATE TABLE IF NOT EXISTS diff_previews (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    previews JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_diff_previews_workspace_created
    ON diff_previews (workspace_id, created_at DESC);
ALTER TABLE diff_previews ENABLE ROW LEVEL SECURITY;
ALTER TABLE diff_previews FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS diff_previews_isolation ON diff_previews;
CREATE POLICY diff_previews_isolation ON diff_previews
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
