-- ADS-009 只读边界审计：记录被允许或拒绝的广告动作，不提供任何外部写入能力。
CREATE TABLE IF NOT EXISTS advertising_boundary_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    action TEXT NOT NULL,
    allowed BOOLEAN NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ad_boundary_workspace_created
    ON advertising_boundary_audits (workspace_id, created_at DESC);
