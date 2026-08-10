-- 隔离记录保留原始行和原因，分析查询只能使用通过质量检查的事实集合。
CREATE TABLE IF NOT EXISTS quality_isolation_records (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    row_index INTEGER NOT NULL,
    reason TEXT NOT NULL,
    record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quality_isolation_scope
    ON quality_isolation_records (organization_id, workspace_id, created_at DESC);
ALTER TABLE quality_isolation_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_isolation_records FORCE ROW LEVEL SECURITY;
CREATE POLICY quality_isolation_org_policy ON quality_isolation_records
    USING (organization_id = current_setting('app.organization_id', true));
