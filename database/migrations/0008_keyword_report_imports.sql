-- RES-003：搜索词导入批次。文件指纹在工作区内唯一，重复提交不得生成重复导入事实。
BEGIN;

CREATE TABLE IF NOT EXISTS keyword_report_imports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    fingerprint CHAR(64) NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    source TEXT NOT NULL DEFAULT 'operator_imported' CHECK (source = 'operator_imported'),
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, workspace_id, fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_keyword_imports_workspace_time
    ON keyword_report_imports (workspace_id, created_at DESC);

ALTER TABLE keyword_report_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_report_imports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS keyword_report_imports_isolation ON keyword_report_imports;
CREATE POLICY keyword_report_imports_isolation ON keyword_report_imports
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));

COMMIT;
