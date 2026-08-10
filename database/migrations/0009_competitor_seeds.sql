-- RES-004：受控竞品种子，仅保存运营人员明确维护的少量公开页面。
BEGIN;

CREATE TABLE IF NOT EXISTS competitor_seeds (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'blocked')),
    last_sampled_at TIMESTAMPTZ,
    stop_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, workspace_id, url)
);

CREATE INDEX IF NOT EXISTS idx_competitor_seeds_workspace_status
    ON competitor_seeds (workspace_id, status, created_at DESC);

ALTER TABLE competitor_seeds ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_seeds FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS competitor_seeds_isolation ON competitor_seeds;
CREATE POLICY competitor_seeds_isolation ON competitor_seeds
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));

COMMIT;
