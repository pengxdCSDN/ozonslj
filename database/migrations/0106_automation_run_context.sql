-- 为同步任务接入受控自动化运行上下文，防止跨页面联动产生重复任务或死循环。
BEGIN;

ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS root_run_id TEXT;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS parent_run_id TEXT;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS trigger_source TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS data_version TEXT;
ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS trigger_depth INTEGER NOT NULL DEFAULT 0;

ALTER TABLE sync_jobs DROP CONSTRAINT IF EXISTS sync_jobs_trigger_depth_check;
ALTER TABLE sync_jobs ADD CONSTRAINT sync_jobs_trigger_depth_check CHECK (trigger_depth >= 0);

-- 历史任务没有运行上下文，先保持可读；新任务由应用层以任务 ID 填充 run/root。
UPDATE sync_jobs
SET run_id = COALESCE(run_id, id),
    root_run_id = COALESCE(root_run_id, id),
    data_version = COALESCE(data_version, id)
WHERE run_id IS NULL OR root_run_id IS NULL OR data_version IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_jobs_run_scope
    ON sync_jobs (organization_id, workspace_id, root_run_id, resource_type, data_version)
    WHERE root_run_id IS NOT NULL AND data_version IS NOT NULL;

COMMENT ON COLUMN sync_jobs.run_id IS '本次自动化运行唯一标识；用于重复消息去重和完整链路追踪。';
COMMENT ON COLUMN sync_jobs.root_run_id IS '触发链根运行标识；同一根任务下的自动化结果不得重复成功。';
COMMENT ON COLUMN sync_jobs.parent_run_id IS '直接父任务运行标识；展示刷新不得作为业务父任务。';
COMMENT ON COLUMN sync_jobs.trigger_source IS '触发来源；页面刷新不得作为业务触发来源。';
COMMENT ON COLUMN sync_jobs.data_version IS '本次任务消费的数据版本或导入批次标识，用于幂等和回读。';
COMMENT ON COLUMN sync_jobs.trigger_depth IS '自动化触发链深度；超过编排上限必须熔断并转人工。';

COMMIT;
