-- AI-005 广告分析快照：保存指标分析和建议，建议不直接执行广告写入。
CREATE TABLE IF NOT EXISTS advertising_analysis_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    inputs JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_advertising_analysis_workspace_created
    ON advertising_analysis_snapshots (workspace_id, created_at DESC);
