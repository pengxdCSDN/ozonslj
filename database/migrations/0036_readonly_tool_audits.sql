-- AI-002 只读工具审计：仅记录工具名称、允许结果和安全原因，不执行动态 SQL。
CREATE TABLE IF NOT EXISTS readonly_tool_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,
    tool TEXT NOT NULL,
    allowed BOOLEAN NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_readonly_tool_audits_created
    ON readonly_tool_audits (created_at DESC);
