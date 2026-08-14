-- 公开样本快照只保存规范化公开字段；原始 HTML 不落库，避免越界保存敏感内容。
CREATE TABLE IF NOT EXISTS public_snapshots (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    seed_id TEXT REFERENCES competitor_seeds(id) ON DELETE SET NULL,
    url TEXT NOT NULL,
    sampled_at TIMESTAMPTZ NOT NULL,
    title TEXT,
    price_minor BIGINT CHECK (price_minor IS NULL OR price_minor >= 0),
    currency TEXT,
    rating NUMERIC(3, 2) CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    review_count INTEGER CHECK (review_count IS NULL OR review_count >= 0),
    image_url TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    sample_size INTEGER NOT NULL CHECK (sample_size > 0),
    estimated BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_public_snapshots_workspace_sampled
    ON public_snapshots (workspace_id, sampled_at DESC);
ALTER TABLE public_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public_snapshots FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_snapshots_isolation ON public_snapshots;
CREATE POLICY public_snapshots_isolation ON public_snapshots
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
