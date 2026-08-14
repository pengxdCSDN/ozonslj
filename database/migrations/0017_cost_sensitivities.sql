-- 成本敏感性结果保留场景变化比例，便于复盘当时的输入假设。
CREATE TABLE IF NOT EXISTS cost_sensitivities (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    input_assumptions JSONB NOT NULL,
    scenarios JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cost_sensitivities_workspace_created
    ON cost_sensitivities (workspace_id, created_at DESC);
ALTER TABLE cost_sensitivities ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_sensitivities FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS cost_sensitivities_isolation ON cost_sensitivities;
CREATE POLICY cost_sensitivities_isolation ON cost_sensitivities
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
