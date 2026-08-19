-- RAG 历史任务归档边界。
-- 归档只改变任务在运营列表中的可见性，不改变任务状态或错误事实；清理只能作用于
-- 已归档且已终结的失败/取消任务，避免误删排队、运行中或成功任务。

ALTER TABLE rag_ingestion_jobs
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_rag_jobs_archive
    ON rag_ingestion_jobs (organization_id, archived_at, finished_at DESC)
    WHERE archived_at IS NOT NULL;

COMMENT ON COLUMN rag_ingestion_jobs.archived_at IS
    '运营归档时间；非空任务默认从当前任务列表隐藏，但仍保留用于审计和问题复盘。';
