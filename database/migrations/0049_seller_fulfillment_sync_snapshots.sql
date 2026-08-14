-- DAT-012 Seller FBO/FBS 履约同步快照：保留履约状态和数量摘要，默认只读干跑。
CREATE TABLE IF NOT EXISTS seller_fulfillment_sync_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    cursor TEXT,
    total INTEGER NOT NULL CHECK (total >= 0),
    items JSONB NOT NULL,
    source TEXT NOT NULL DEFAULT 'seller_api',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_seller_fulfillment_workspace_created
    ON seller_fulfillment_sync_snapshots (workspace_id, created_at DESC);
