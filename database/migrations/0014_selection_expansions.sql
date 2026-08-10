-- Expand 候选保存分层词和变体结果，后续需人工确认后才能进入 Validate。
CREATE TABLE IF NOT EXISTS selection_expansions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    seed_product TEXT NOT NULL,
    core_terms JSONB NOT NULL,
    attribute_terms JSONB NOT NULL,
    scene_terms JSONB NOT NULL,
    variant_candidates JSONB NOT NULL,
    estimated BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_selection_expansions_workspace_created
    ON selection_expansions (workspace_id, created_at DESC);
ALTER TABLE selection_expansions ENABLE ROW LEVEL SECURITY;
ALTER TABLE selection_expansions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS selection_expansions_isolation ON selection_expansions;
CREATE POLICY selection_expansions_isolation ON selection_expansions
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
