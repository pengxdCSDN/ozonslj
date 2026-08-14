-- AI-007 报告快照：日报、周报和月报共用结构，待办只作为建议，不自动执行。
CREATE TABLE IF NOT EXISTS summary_report_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    report_type TEXT NOT NULL CHECK (report_type IN ('daily', 'weekly', 'monthly')),
    period TEXT NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_summary_reports_workspace_period
    ON summary_report_snapshots (workspace_id, period DESC);
