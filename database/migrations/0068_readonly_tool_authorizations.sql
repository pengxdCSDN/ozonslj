-- 保存只读工具授权和参数过滤结果；该表不提供 SQL 执行能力。
CREATE TABLE IF NOT EXISTS readonly_tool_authorizations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,
    allowed BOOLEAN NOT NULL,
    parameters JSONB NOT NULL,
    reason TEXT NOT NULL,
    sql_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_readonly_tool_workspace_created
    ON readonly_tool_authorizations (workspace_id, created_at DESC);
ALTER TABLE readonly_tool_authorizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE readonly_tool_authorizations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS readonly_tool_isolation ON readonly_tool_authorizations;
CREATE POLICY readonly_tool_isolation ON readonly_tool_authorizations
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
