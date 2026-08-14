-- AI-006 竞品与选品分析快照：保留样本范围和估算声明，不覆盖官方销售事实。
CREATE TABLE IF NOT EXISTS competitor_selection_analysis_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    source_window TEXT NOT NULL,
    inputs JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_competitor_selection_workspace_created
    ON competitor_selection_analysis_snapshots (workspace_id, created_at DESC);
