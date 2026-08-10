-- 为同步任务增加幂等、重试与租约字段。PostgreSQL 保存任务事实，Redis 仅负责可重建投递。
BEGIN;

ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS requested_user_id TEXT;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0
    CHECK (attempt_count >= 0);
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 3
    CHECK (max_attempts BETWEEN 1 AND 10);
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ NOT NULL
    DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS lease_owner TEXT;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS cancel_requested_at TIMESTAMPTZ;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL
    DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE sync_jobs
    ADD CONSTRAINT sync_jobs_requested_user_same_org_fk
    FOREIGN KEY (organization_id, requested_user_id)
    REFERENCES organization_members(organization_id, user_id) ON DELETE SET NULL;

-- 同一工作区内相同幂等键永久对应同一创建结果，避免网络重试生成重复任务。
CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_jobs_idempotency
    ON sync_jobs (organization_id, workspace_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- Scheduler 扫描到期排队任务；Worker 扫描过期租约以恢复中断任务。
CREATE INDEX IF NOT EXISTS idx_sync_jobs_dispatch
    ON sync_jobs (organization_id, status, next_attempt_at, created_at)
    WHERE status = 'queued';
CREATE INDEX IF NOT EXISTS idx_sync_jobs_expired_lease
    ON sync_jobs (organization_id, lease_expires_at)
    WHERE status = 'running';

COMMENT ON COLUMN sync_jobs.idempotency_key IS '创建任务的客户端幂等键；同一工作区重复提交返回原任务。';
COMMENT ON COLUMN sync_jobs.next_attempt_at IS 'Scheduler 可重新投递任务的最早 UTC 时间。';
COMMENT ON COLUMN sync_jobs.lease_expires_at IS 'Worker 租约到期时间；过期任务可由恢复流程重新领取。';
COMMENT ON COLUMN sync_jobs.error_message IS '仅保存脱敏错误摘要，禁止凭据、客户信息和上游原始响应。';

COMMIT;
