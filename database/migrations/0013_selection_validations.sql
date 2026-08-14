-- Validate 结果保存模型假设和输出快照，便于回溯利润计算，不覆盖官方财务事实。
CREATE TABLE IF NOT EXISTS selection_validations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    sku TEXT NOT NULL,
    input_assumptions JSONB NOT NULL,
    result_snapshot JSONB NOT NULL,
    incomplete BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_selection_validations_workspace_created
    ON selection_validations (workspace_id, created_at DESC);
ALTER TABLE selection_validations ENABLE ROW LEVEL SECURITY;
ALTER TABLE selection_validations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS selection_validations_isolation ON selection_validations;
CREATE POLICY selection_validations_isolation ON selection_validations
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
