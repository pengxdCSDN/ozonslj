-- 广告指标快照保存公式输入结果、窗口、币种和完整度，避免跨窗口混算。
CREATE TABLE IF NOT EXISTS advertising_metric_snapshots (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    -- 统计窗口是可查询业务维度；使用明确列名，避免 PostgreSQL WINDOW 保留字。
    metric_window TEXT NOT NULL,
    currency TEXT NOT NULL,
    inputs JSONB NOT NULL,
    metrics JSONB NOT NULL,
    complete BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_advertising_metric_snapshots_workspace_created
    ON advertising_metric_snapshots (workspace_id, metric_window, created_at DESC);
ALTER TABLE advertising_metric_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertising_metric_snapshots FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS advertising_metric_snapshots_isolation ON advertising_metric_snapshots;
CREATE POLICY advertising_metric_snapshots_isolation ON advertising_metric_snapshots
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
