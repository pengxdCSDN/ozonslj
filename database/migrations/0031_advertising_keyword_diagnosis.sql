-- ADS-006 关键词诊断快照：保存输入与分类结果，便于复盘规则版本；不保存或执行任何广告写命令。
CREATE TABLE IF NOT EXISTS advertising_keyword_diagnosis_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    threshold_version TEXT NOT NULL DEFAULT 'v1',
    inputs JSONB NOT NULL,
    diagnoses JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ad_keyword_diagnosis_workspace_created
    ON advertising_keyword_diagnosis_snapshots (workspace_id, created_at DESC);
