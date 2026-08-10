-- Seller 同步快照约束：映射层拒绝异常数据，数据库层继续保护历史快照不被写入非法结构。
-- items 必须是 JSON 数组；source 仅允许官方 Seller API，避免把估算或导入数据伪装成官方事实。
ALTER TABLE seller_product_sync_snapshots
    ADD CONSTRAINT seller_product_snapshot_items_array
    CHECK (jsonb_typeof(items) = 'array'),
    ADD CONSTRAINT seller_product_snapshot_source_official
    CHECK (source = 'seller_api'),
    ADD CONSTRAINT seller_product_snapshot_cursor_nonblank
    CHECK (cursor IS NULL OR length(btrim(cursor)) > 0);

ALTER TABLE seller_stock_sync_snapshots
    ADD CONSTRAINT seller_stock_snapshot_items_array
    CHECK (jsonb_typeof(items) = 'array'),
    ADD CONSTRAINT seller_stock_snapshot_source_official
    CHECK (source = 'seller_api'),
    ADD CONSTRAINT seller_stock_snapshot_cursor_nonblank
    CHECK (cursor IS NULL OR length(btrim(cursor)) > 0);

ALTER TABLE seller_order_sync_snapshots
    ADD CONSTRAINT seller_order_snapshot_items_array
    CHECK (jsonb_typeof(items) = 'array'),
    ADD CONSTRAINT seller_order_snapshot_source_official
    CHECK (source = 'seller_api'),
    ADD CONSTRAINT seller_order_snapshot_cursor_nonblank
    CHECK (cursor IS NULL OR length(btrim(cursor)) > 0);

ALTER TABLE seller_fulfillment_sync_snapshots
    ADD CONSTRAINT seller_fulfillment_snapshot_items_array
    CHECK (jsonb_typeof(items) = 'array'),
    ADD CONSTRAINT seller_fulfillment_snapshot_source_official
    CHECK (source = 'seller_api'),
    ADD CONSTRAINT seller_fulfillment_snapshot_cursor_nonblank
    CHECK (cursor IS NULL OR length(btrim(cursor)) > 0);
