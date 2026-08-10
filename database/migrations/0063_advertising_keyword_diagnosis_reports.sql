-- 保存关键词诊断快照，便于复盘阈值和广告效果；不保存任何可执行广告写命令。
CREATE TABLE IF NOT EXISTS advertising_keyword_diagnosis_reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    diagnoses JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ad_keyword_diagnosis_workspace_created
    ON advertising_keyword_diagnosis_reports (workspace_id, created_at DESC);
ALTER TABLE advertising_keyword_diagnosis_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertising_keyword_diagnosis_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ad_keyword_diagnosis_isolation ON advertising_keyword_diagnosis_reports;
CREATE POLICY ad_keyword_diagnosis_isolation ON advertising_keyword_diagnosis_reports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
