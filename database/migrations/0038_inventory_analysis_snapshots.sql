-- AI-004 库存分析快照：保存库存输入与建议，原始库存事实仍来自库存同步结果。
CREATE TABLE IF NOT EXISTS inventory_analysis_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    inputs JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_inventory_analysis_workspace_created
    ON inventory_analysis_snapshots (workspace_id, created_at DESC);
