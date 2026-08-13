-- RAG-025：保存 Ozon 俄文原文与云端中文译文的独立版本。
-- 俄文是上游事实，不允许被翻译结果覆盖；译文失败时仍可展示原文并稍后重试。
BEGIN;

ALTER TABLE product_offers
    ADD COLUMN IF NOT EXISTS name_zh TEXT,
    ADD COLUMN IF NOT EXISTS description_ru TEXT,
    ADD COLUMN IF NOT EXISTS description_zh TEXT,
    ADD COLUMN IF NOT EXISTS attributes_ru JSONB,
    ADD COLUMN IF NOT EXISTS attributes_zh JSONB,
    ADD COLUMN IF NOT EXISTS translation_status TEXT NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS translation_model TEXT,
    ADD COLUMN IF NOT EXISTS translation_source_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS translated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS translation_error TEXT,
    ADD COLUMN IF NOT EXISTS embedding_text TEXT,
    ADD COLUMN IF NOT EXISTS embedding_profile_id TEXT;

ALTER TABLE product_offers
    DROP CONSTRAINT IF EXISTS product_offers_translation_status_check;
ALTER TABLE product_offers
    ADD CONSTRAINT product_offers_translation_status_check
    CHECK (translation_status IN ('pending', 'succeeded', 'failed', 'not_required'));

ALTER TABLE product_offers
    DROP CONSTRAINT IF EXISTS product_offers_translation_hash_check;
ALTER TABLE product_offers
    ADD CONSTRAINT product_offers_translation_hash_check
    CHECK (translation_source_hash IS NULL OR translation_source_hash ~ '^[0-9a-f]{64}$');

COMMENT ON COLUMN product_offers.name IS
    'Ozon 返回的商品原始名称；通常为俄文，禁止用中文译文覆盖。';
COMMENT ON COLUMN product_offers.name_zh IS
    '云端生成的简体中文商品名称；可重新生成，缺失时必须回退显示俄文原文。';
COMMENT ON COLUMN product_offers.description_ru IS
    'Ozon 商品俄文描述原文；用于证据追溯和中俄双语检索。';
COMMENT ON COLUMN product_offers.description_zh IS
    '云端生成的中文描述派生物；不作为 Ozon 原始事实来源。';
COMMENT ON COLUMN product_offers.attributes_ru IS
    'Ozon 属性的俄文原始键值；品牌、型号、SKU、数字和单位必须保持原值。';
COMMENT ON COLUMN product_offers.attributes_zh IS
    '属性键值的中文展示副本；翻译失败或字段不适合翻译时可以为空。';
COMMENT ON COLUMN product_offers.translation_status IS
    '翻译状态：pending 待处理、succeeded 成功、failed 失败、not_required 不需要翻译。';
COMMENT ON COLUMN product_offers.translation_model IS
    '生成中文译文的云端模型标识；用于版本追踪，禁止写入 API Key。';
COMMENT ON COLUMN product_offers.translation_source_hash IS
    '俄文原文规范化后的 SHA-256 指纹；源内容变化时必须重新翻译。';
COMMENT ON COLUMN product_offers.translated_at IS
    '最近一次成功生成中文译文的 UTC 时间；失败重试不得伪造成功时间。';
COMMENT ON COLUMN product_offers.translation_error IS
    '脱敏后的最近一次翻译失败摘要；不得保存请求头、API Key 或完整供应商响应。';
COMMENT ON COLUMN product_offers.embedding_text IS
    '用于中俄双语向量化的派生文本；由中文译文和俄文原文拼接生成，可按指纹重建。';
COMMENT ON COLUMN product_offers.embedding_profile_id IS
    '向量模型、维度和预处理配置的版本标识；变更时必须建立新索引并完整重建。';

CREATE INDEX IF NOT EXISTS idx_product_offers_translation_queue
    ON product_offers (workspace_id, translation_status, synced_at)
    WHERE translation_status IN ('pending', 'failed');

COMMIT;
