-- 保存 Agent 定时、事件和手动触发配置。
CREATE TABLE IF NOT EXISTS agent_triggers (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('scheduled', 'event', 'manual')),
    target TEXT NOT NULL,
    schedule TEXT,
    event_name TEXT,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    read_only BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_triggers_workspace_created
    ON agent_triggers (workspace_id, created_at DESC);
ALTER TABLE agent_triggers ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_triggers FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS agent_triggers_isolation ON agent_triggers;
CREATE POLICY agent_triggers_isolation ON agent_triggers
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
