-- AI-008 Agent 触发器：保存周期、事件或手动触发配置；触发本身不会越过只读工具边界。
CREATE TABLE IF NOT EXISTS agent_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('scheduled', 'event', 'manual')),
    target TEXT NOT NULL,
    schedule TEXT,
    event_name TEXT,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    read_only BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agent_triggers_workspace_enabled
    ON agent_triggers (workspace_id, enabled);
