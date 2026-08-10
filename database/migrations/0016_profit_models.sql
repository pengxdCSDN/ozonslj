-- 利润模型保存每次输入和 FBO/FBS 输出快照，所有金额均为最小货币单位整数。
CREATE TABLE IF NOT EXISTS profit_models (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    input_assumptions JSONB NOT NULL,
    fbo_result JSONB NOT NULL,
    fbs_result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_profit_models_workspace_created
    ON profit_models (workspace_id, created_at DESC);
ALTER TABLE profit_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE profit_models FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS profit_models_isolation ON profit_models;
CREATE POLICY profit_models_isolation ON profit_models
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
