-- 审计事件只追加不更新，记录受控写入链路的关键阶段和操作者可追溯信息。
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    detail JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_events_scope ON audit_events
    (organization_id, workspace_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_subject ON audit_events
    (organization_id, subject_id, occurred_at DESC);
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_events_org_policy ON audit_events
    USING (organization_id = current_setting('app.organization_id', true));
