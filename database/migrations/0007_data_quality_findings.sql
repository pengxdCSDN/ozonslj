-- DQ-007：数据质量隔离区。异常事实保留诊断信息，但不覆盖业务事实。
BEGIN;

CREATE TABLE IF NOT EXISTS data_quality_findings (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    rule_code TEXT NOT NULL,
    field_name TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('warning', 'error')),
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'accepted', 'resolved', 'ignored')),
    source TEXT NOT NULL DEFAULT 'derived_quality' CHECK (source = 'derived_quality'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,
    FOREIGN KEY (workspace_id) REFERENCES store_workspaces(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quality_findings_workspace_status
    ON data_quality_findings (workspace_id, status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_quality_findings_open_fingerprint
    ON data_quality_findings (organization_id, workspace_id, rule_code, field_name, message)
    WHERE status = 'open';

ALTER TABLE data_quality_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_quality_findings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS data_quality_findings_isolation ON data_quality_findings;
CREATE POLICY data_quality_findings_isolation ON data_quality_findings
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));

COMMENT ON TABLE data_quality_findings IS
    '数据质量隔离记录；只保存规则、字段和脱敏摘要，不把异常事实写回商品/库存/订单事实表。';
COMMENT ON COLUMN data_quality_findings.status IS
    '隔离处理状态；open 才进入待处理列表，resolved/ignored 不得重新覆盖业务事实。';

COMMIT;
