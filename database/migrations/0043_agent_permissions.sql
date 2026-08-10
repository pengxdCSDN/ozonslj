-- AI-009 Agent 权限快照：永久只读，不授予 SQL、凭据或外部写入权限。
CREATE TABLE IF NOT EXISTS agent_permission_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    agent TEXT NOT NULL,
    allowed_capabilities JSONB NOT NULL,
    denied_capabilities JSONB NOT NULL,
    sql_access BOOLEAN NOT NULL DEFAULT FALSE,
    credential_access BOOLEAN NOT NULL DEFAULT FALSE,
    external_write_access BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agent_permissions_workspace_created
    ON agent_permission_snapshots (workspace_id, created_at DESC);
