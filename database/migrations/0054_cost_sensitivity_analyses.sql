-- SEL-006：保存成本敏感性输入和场景结果，确保利润判断可回溯。
BEGIN;
CREATE TABLE IF NOT EXISTS cost_sensitivity_analyses (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    input_assumptions JSONB NOT NULL,
    scenarios JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cost_sensitivity_workspace_created
    ON cost_sensitivity_analyses (workspace_id, created_at DESC);
ALTER TABLE cost_sensitivity_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_sensitivity_analyses FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS cost_sensitivity_isolation ON cost_sensitivity_analyses;
CREATE POLICY cost_sensitivity_isolation ON cost_sensitivity_analyses
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
COMMIT;
