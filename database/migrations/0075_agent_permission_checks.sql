-- 保存 Agent 权限判定，确保 SQL、凭据和外部写入永久拒绝。
CREATE TABLE IF NOT EXISTS agent_permission_checks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,
    decision JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_permission_workspace_created
    ON agent_permission_checks (workspace_id, created_at DESC);
ALTER TABLE agent_permission_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_permission_checks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS agent_permission_isolation ON agent_permission_checks;
CREATE POLICY agent_permission_isolation ON agent_permission_checks
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
