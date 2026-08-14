-- DQ-003 缺失与枚举质量快照：问题进入隔离流程，不静默参与业务分析。
CREATE TABLE IF NOT EXISTS data_quality_schema_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    checked_rows INTEGER NOT NULL CHECK (checked_rows >= 0),
    findings JSONB NOT NULL,
    valid BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_quality_schema_workspace_created
    ON data_quality_schema_snapshots (workspace_id, created_at DESC);
