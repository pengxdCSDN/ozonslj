-- 记录广告只读边界检查，包括被拒绝的写入动作。
CREATE TABLE IF NOT EXISTS advertising_boundary_checks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    allowed BOOLEAN NOT NULL,
    reason TEXT NOT NULL,
    audit_required BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ad_boundary_workspace_created
    ON advertising_boundary_checks (workspace_id, created_at DESC);
ALTER TABLE advertising_boundary_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertising_boundary_checks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ad_boundary_isolation ON advertising_boundary_checks;
CREATE POLICY ad_boundary_isolation ON advertising_boundary_checks
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
