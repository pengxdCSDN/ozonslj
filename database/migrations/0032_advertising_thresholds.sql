-- ADS-007 阈值版本：记录每次诊断使用的组织工作区阈值，禁止覆盖历史版本。
CREATE TABLE IF NOT EXISTS advertising_threshold_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    min_impressions INTEGER NOT NULL CHECK (min_impressions >= 0),
    min_clicks INTEGER NOT NULL CHECK (min_clicks >= 0),
    high_cvr_percent NUMERIC(12,4) NOT NULL CHECK (high_cvr_percent >= 0),
    high_spend_minor BIGINT NOT NULL CHECK (high_spend_minor >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, version)
);
