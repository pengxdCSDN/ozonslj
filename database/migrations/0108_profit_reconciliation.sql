-- 保存利润预计值与只读财务实际值的对账事实；预览结果只有显式批次落库后才成为事实。
BEGIN;

CREATE TABLE IF NOT EXISTS profit_reconciliation_batches (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('completed', 'partial', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_profit_reconciliation_batch_key
    ON profit_reconciliation_batches (organization_id, workspace_id, idempotency_key);

CREATE TABLE IF NOT EXISTS profit_reconciliation_records (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    batch_id TEXT NOT NULL REFERENCES profit_reconciliation_batches(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES store_workspaces(id) ON DELETE CASCADE,
    order_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    estimated_profit_minor BIGINT,
    actual_profit_minor BIGINT,
    variance_minor BIGINT,
    side TEXT NOT NULL CHECK (side IN ('matched', 'missing_estimated', 'missing_actual')),
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (estimated_profit_minor IS NOT NULL OR actual_profit_minor IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_profit_reconciliation_record_key
    ON profit_reconciliation_records (organization_id, batch_id, order_id, sku_id);
CREATE INDEX IF NOT EXISTS idx_profit_reconciliation_records_workspace
    ON profit_reconciliation_records (organization_id, workspace_id, created_at DESC);

COMMENT ON TABLE profit_reconciliation_batches IS '利润对账批次事实；预览数据未显式保存前不进入业务事实。';
COMMENT ON TABLE profit_reconciliation_records IS '订单/SKU 预计与实际利润差异；缺失侧必须显式标记，不允许猜测补值。';
COMMENT ON COLUMN profit_reconciliation_records.side IS 'matched 表示双方存在；missing_* 表示只存在一侧。';

COMMIT;
