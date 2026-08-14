-- 保存受控发布命令及回读结果；幂等键确保重复提交不会产生第二条命令。
CREATE TABLE IF NOT EXISTS listing_publish_commands (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'executed', 'partial', 'rejected')),
    requested_text TEXT NOT NULL,
    readback_text TEXT,
    matched BOOLEAN NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_listing_publish_workspace_created
    ON listing_publish_commands (workspace_id, product_scope, created_at DESC);
ALTER TABLE listing_publish_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_publish_commands FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_publish_commands_isolation ON listing_publish_commands;
CREATE POLICY listing_publish_commands_isolation ON listing_publish_commands
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
