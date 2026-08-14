-- 保存外部写入后的回读核对证据；差异必须保留，不能被成功状态覆盖。
CREATE TABLE IF NOT EXISTS readback_verifications (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    verification JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_readback_verifications_scope
    ON readback_verifications (organization_id, workspace_id, created_at DESC);
ALTER TABLE readback_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE readback_verifications FORCE ROW LEVEL SECURITY;
CREATE POLICY readback_verifications_org_policy ON readback_verifications
    USING (organization_id = current_setting('app.organization_id', true));
