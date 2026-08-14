-- DAT-010 Seller 库存同步快照：保存只读规范化结果，异常库存不静默覆盖历史事实。
CREATE TABLE IF NOT EXISTS seller_stock_sync_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    cursor TEXT,
    total INTEGER NOT NULL CHECK (total >= 0),
    items JSONB NOT NULL,
    source TEXT NOT NULL DEFAULT 'seller_api',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_seller_stock_sync_workspace_created
    ON seller_stock_sync_snapshots (workspace_id, created_at DESC);
