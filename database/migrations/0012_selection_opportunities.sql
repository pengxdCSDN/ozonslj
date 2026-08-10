-- Explore 候选是推导结果，保存输入摘要和估算标记，不能覆盖官方商品事实。
CREATE TABLE IF NOT EXISTS selection_opportunities (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    score NUMERIC(6, 2) NOT NULL,
    search_count INTEGER NOT NULL,
    sample_count INTEGER NOT NULL,
    conversion_rate NUMERIC(8, 4),
    median_price_minor BIGINT,
    own_coverage_gap BOOLEAN NOT NULL,
    estimated BOOLEAN NOT NULL DEFAULT TRUE,
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_selection_opportunities_workspace_score
    ON selection_opportunities (workspace_id, score DESC, created_at DESC);
ALTER TABLE selection_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE selection_opportunities FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS selection_opportunities_isolation ON selection_opportunities;
CREATE POLICY selection_opportunities_isolation ON selection_opportunities
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
