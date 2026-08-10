-- SEL-008：固定章节商品立项决策书；仅保存建议，不允许自动执行外部写入。
BEGIN;
CREATE TABLE IF NOT EXISTS selection_decision_books (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    content JSONB NOT NULL,
    confirmation_status TEXT NOT NULL CHECK (confirmation_status IN ('pending', 'confirmed', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_selection_decision_books_workspace_created
    ON selection_decision_books (workspace_id, created_at DESC);
ALTER TABLE selection_decision_books ENABLE ROW LEVEL SECURITY;
ALTER TABLE selection_decision_books FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS selection_decision_books_isolation ON selection_decision_books;
CREATE POLICY selection_decision_books_isolation ON selection_decision_books
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
COMMIT;
