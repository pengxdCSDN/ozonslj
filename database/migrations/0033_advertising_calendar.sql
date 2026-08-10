-- ADS-008 建议日历快照：保存生成起点与 30 天只读建议，便于复盘历史计划。
CREATE TABLE IF NOT EXISTS advertising_calendar_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    start_date DATE NOT NULL,
    days JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ad_calendar_workspace_created
    ON advertising_calendar_snapshots (workspace_id, created_at DESC);
