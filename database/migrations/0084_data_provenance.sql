-- 来源标签是分析可信度的基础；所有进入业务分析的数据都必须保留来源、时间和口径说明。
CREATE TABLE IF NOT EXISTS data_provenance (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id UUID NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('official_private', 'operator_imported', 'public_sample', 'derived_estimate')),
    observed_at TIMESTAMPTZ NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_data_provenance_scope ON data_provenance
    (organization_id, workspace_id, observed_at DESC);
ALTER TABLE data_provenance ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_provenance FORCE ROW LEVEL SECURITY;
CREATE POLICY data_provenance_org_policy ON data_provenance
    USING (organization_id = current_setting('app.organization_id', true));
