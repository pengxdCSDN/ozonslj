-- 跨来源冲突单独留痕，官方事实不得被导入值或公开估算静默覆盖。
CREATE TABLE IF NOT EXISTS source_conflicts (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    conflict JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_source_conflicts_scope
    ON source_conflicts (organization_id, workspace_id, created_at DESC);
ALTER TABLE source_conflicts ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_conflicts FORCE ROW LEVEL SECURITY;
CREATE POLICY source_conflicts_org_policy ON source_conflicts
    USING (organization_id = current_setting('app.organization_id', true));
