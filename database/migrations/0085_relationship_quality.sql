-- 关系与时间质量检查结果进入隔离区，不覆盖业务事实，也不静默参与分析。
CREATE TABLE IF NOT EXISTS relationship_quality_findings (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    finding JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_relationship_quality_scope
    ON relationship_quality_findings (organization_id, workspace_id, created_at DESC);
ALTER TABLE relationship_quality_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationship_quality_findings FORCE ROW LEVEL SECURITY;
CREATE POLICY relationship_quality_org_policy ON relationship_quality_findings
    USING (organization_id = current_setting('app.organization_id', true));
