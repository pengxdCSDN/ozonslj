-- 竞争度是基于公开样本的推导结果，必须保留估算标记和样本范围。
CREATE TABLE IF NOT EXISTS competition_analyses (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    sample_count INTEGER NOT NULL,
    competition_score NUMERIC(6, 2) NOT NULL,
    median_price_minor BIGINT,
    price_band_low_minor BIGINT,
    price_band_high_minor BIGINT,
    seller_concentration_percent NUMERIC(6, 2) NOT NULL,
    brand_concentration_percent NUMERIC(6, 2) NOT NULL,
    estimated BOOLEAN NOT NULL DEFAULT TRUE,
    caveat TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_competition_analyses_workspace_created
    ON competition_analyses (workspace_id, created_at DESC);
ALTER TABLE competition_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE competition_analyses FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS competition_analyses_isolation ON competition_analyses;
CREATE POLICY competition_analyses_isolation ON competition_analyses
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
