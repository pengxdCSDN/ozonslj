-- 解析变化告警保留前后值，便于运营复核页面结构变化；不保存原始 HTML。
CREATE TABLE IF NOT EXISTS parser_alerts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('warning', 'error')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'ignored')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_parser_alerts_workspace_status
    ON parser_alerts (workspace_id, status, created_at DESC);
ALTER TABLE parser_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE parser_alerts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS parser_alerts_isolation ON parser_alerts;
CREATE POLICY parser_alerts_isolation ON parser_alerts
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
