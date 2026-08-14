-- 发布命令必须经过审核，使用幂等键，执行后必须记录回读结果和部分失败状态。
CREATE TABLE IF NOT EXISTS listing_publish_commands (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    product_scope TEXT NOT NULL,
    version INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'executed', 'partial', 'rejected')),
    requested_text TEXT NOT NULL,
    readback_text TEXT,
    matched BOOLEAN NOT NULL DEFAULT FALSE,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, workspace_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_listing_publish_commands_workspace_created
    ON listing_publish_commands (workspace_id, product_scope, created_at DESC);
ALTER TABLE listing_publish_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_publish_commands FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS listing_publish_commands_isolation ON listing_publish_commands;
CREATE POLICY listing_publish_commands_isolation ON listing_publish_commands
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
