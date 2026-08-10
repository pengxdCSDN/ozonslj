-- AI-003 销售分析快照：保存窗口和推导结果，官方销售事实仍由 Seller 数据表维护。
CREATE TABLE IF NOT EXISTS sales_analysis_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    current_window TEXT NOT NULL,
    previous_window TEXT NOT NULL,
    inputs JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sales_analysis_workspace_created
    ON sales_analysis_snapshots (workspace_id, created_at DESC);
