-- RAG-评测持久化队列：API 只创建事实，Scheduler 投递唤醒，Worker 通过租约执行。
BEGIN;

ALTER TABLE rag_evaluation_runs
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    ADD COLUMN IF NOT EXISTS lease_owner TEXT,
    ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS error_code TEXT;

-- 旧版本把门禁阻断批次也保存成 queued，导致页面误显示“等待执行”。
-- blocked 是终态展示值；只有 gate_status=ready 的批次允许进入 Worker 队列。
ALTER TABLE rag_evaluation_runs DROP CONSTRAINT IF EXISTS rag_evaluation_runs_status_check;
ALTER TABLE rag_evaluation_runs
    ADD CONSTRAINT rag_evaluation_runs_status_check
    CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled', 'blocked'));

-- 历史版本把门禁阻断批次和重复 ready 批次都留在 queued；保留审计记录，
-- 只把它们改成明确终态，避免升级后一次性重复调用同一套评测。
UPDATE rag_evaluation_runs
SET status = 'blocked', completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
    error_code = COALESCE(error_code, 'gate_blocked_legacy')
WHERE gate_status = 'blocked' AND status = 'queued';

WITH ranked_active AS (
    SELECT id, ROW_NUMBER() OVER (
        PARTITION BY organization_id, suite
        ORDER BY created_at DESC, id DESC
    ) AS row_number
    FROM rag_evaluation_runs
    WHERE gate_status = 'ready' AND status IN ('queued', 'running')
)
UPDATE rag_evaluation_runs AS runs
SET status = 'cancelled', completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
    error_code = 'duplicate_run_deduplicated', lease_owner = NULL, lease_expires_at = NULL
FROM ranked_active
WHERE runs.id = ranked_active.id AND ranked_active.row_number > 1;

-- 数据库级兜底约束：即使未来有新的入口绕过 API 查询，也不能制造同组织同套件的
-- 两个活动批次。历史重复记录已在上一步转为 cancelled，因此可以安全创建索引。
CREATE UNIQUE INDEX IF NOT EXISTS uq_rag_eval_active_suite
    ON rag_evaluation_runs (organization_id, suite)
    WHERE gate_status = 'ready' AND status IN ('queued', 'running');

CREATE INDEX IF NOT EXISTS idx_rag_eval_dispatch
    ON rag_evaluation_runs (organization_id, status, gate_status, lease_expires_at, created_at);

COMMENT ON COLUMN rag_evaluation_runs.attempt_count IS 'Worker 领取次数；API 重启或租约过期后允许安全接管。';
COMMENT ON COLUMN rag_evaluation_runs.lease_owner IS '当前 Worker 或 Scheduler 租约持有者；不得接受客户端写入。';
COMMENT ON COLUMN rag_evaluation_runs.lease_expires_at IS '任务租约过期时间；过期后由 Scheduler 重新投递。';
COMMENT ON COLUMN rag_evaluation_runs.started_at IS '首次进入 Worker running 状态的时间。';
COMMENT ON COLUMN rag_evaluation_runs.error_code IS '脱敏失败分类；不得保存模型原文、凭据或客户数据。';

COMMIT;
