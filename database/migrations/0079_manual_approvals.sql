-- 人工审批是外部写入前的独立闸门；approved 只代表允许执行，不在此表直接执行 Ozon 写操作。
CREATE TABLE IF NOT EXISTS manual_approvals (
    approval_id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    command_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewer TEXT,
    idempotency_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_manual_approvals_idempotency
    ON manual_approvals (organization_id, workspace_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_manual_approvals_scope ON manual_approvals (organization_id, workspace_id, status);
ALTER TABLE manual_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE manual_approvals FORCE ROW LEVEL SECURITY;
CREATE POLICY manual_approvals_org_policy ON manual_approvals
    USING (organization_id = current_setting('app.organization_id', true));
