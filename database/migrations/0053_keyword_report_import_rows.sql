-- RES-001：保存已通过预览校验的搜索词事实；原始文件不落库，行级事实可供选品分析追溯。
BEGIN;

CREATE TABLE IF NOT EXISTS keyword_report_import_rows (
    id TEXT PRIMARY KEY,
    import_id TEXT NOT NULL REFERENCES keyword_report_imports(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL CHECK (length(trim(keyword)) > 0),
    normalized_keyword TEXT GENERATED ALWAYS AS (lower(trim(keyword))) STORED,
    search_count INTEGER CHECK (search_count IS NULL OR search_count >= 0),
    conversion_rate TEXT,
    source_row INTEGER NOT NULL CHECK (source_row >= 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (import_id, normalized_keyword)
);

CREATE INDEX IF NOT EXISTS idx_keyword_import_rows_import ON keyword_report_import_rows(import_id);
ALTER TABLE keyword_report_import_rows ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_report_import_rows FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS keyword_report_import_rows_isolation ON keyword_report_import_rows;
CREATE POLICY keyword_report_import_rows_isolation ON keyword_report_import_rows
    USING (EXISTS (
        SELECT 1 FROM keyword_report_imports batch
        WHERE batch.id = import_id
          AND batch.organization_id = current_setting('app.organization_id', true)
    ));

COMMIT;
