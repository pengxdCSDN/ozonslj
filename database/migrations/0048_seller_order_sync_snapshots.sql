-- DAT-011 Seller 订单同步快照：保留窗口内的官方订单摘要，金额使用最小货币单位整数。
CREATE TABLE IF NOT EXISTS seller_order_sync_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    cursor TEXT,
    total INTEGER NOT NULL CHECK (total >= 0),
    items JSONB NOT NULL,
    source TEXT NOT NULL DEFAULT 'seller_api',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_seller_order_sync_workspace_created
    ON seller_order_sync_snapshots (workspace_id, created_at DESC);
