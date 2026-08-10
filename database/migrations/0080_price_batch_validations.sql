-- 保存批量价格校验快照，作为人工审批前的可追溯证据；不执行外部写入。
CREATE TABLE IF NOT EXISTS price_batch_validations (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    validation JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_price_batch_validations_scope
    ON price_batch_validations (organization_id, workspace_id, created_at DESC);
ALTER TABLE price_batch_validations ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_batch_validations FORCE ROW LEVEL SECURITY;
CREATE POLICY price_batch_validations_org_policy ON price_batch_validations
    USING (organization_id = current_setting('app.organization_id', true));
