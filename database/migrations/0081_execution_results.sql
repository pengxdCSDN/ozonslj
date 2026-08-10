-- 保存受控执行的逐项结果，允许运营人员定位批量操作中的部分失败。
CREATE TABLE IF NOT EXISTS execution_results (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_execution_results_scope
    ON execution_results (organization_id, workspace_id, created_at DESC);
ALTER TABLE execution_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_results FORCE ROW LEVEL SECURITY;
CREATE POLICY execution_results_org_policy ON execution_results
    USING (organization_id = current_setting('app.organization_id', true));
