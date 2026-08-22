-- 为事实变化事件建立独立的数据质量检查任务事实，避免复用同步任务语义。
BEGIN;

CREATE TABLE IF NOT EXISTS quality_check_jobs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    data_version TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    parent_run_id TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    lease_owner TEXT,
    lease_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_quality_check_jobs_idempotency
    ON quality_check_jobs (organization_id, workspace_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_quality_check_jobs_queue
    ON quality_check_jobs (organization_id, status, created_at);

COMMENT ON TABLE quality_check_jobs IS '由受控事实事件创建的质量检查任务；PostgreSQL 保存事实，Redis 只负责唤醒。';
COMMENT ON COLUMN quality_check_jobs.data_version IS '本次质量检查消费的数据版本，重复版本不得重复创建任务。';
COMMENT ON COLUMN quality_check_jobs.parent_run_id IS '触发该质量检查的同步或事实运行标识，不得指向展示刷新。';

COMMIT;
