-- RAG-026：模型供应商可扩展、用途绑定可覆盖翻译和多级自动降级。
-- 适配器是供应商协议标识，不应把页面示例固化为有限枚举；运行时由客户端能力校验。
BEGIN;

ALTER TABLE rag_model_providers
    DROP CONSTRAINT IF EXISTS rag_model_providers_adapter_type_check;
ALTER TABLE rag_model_providers
    ADD CONSTRAINT rag_model_providers_adapter_type_check
    CHECK (btrim(adapter_type) <> '');

ALTER TABLE rag_model_purpose_bindings
    DROP CONSTRAINT IF EXISTS rag_model_purpose_bindings_purpose_check;
ALTER TABLE rag_model_purpose_bindings
    ADD CONSTRAINT rag_model_purpose_bindings_purpose_check
    CHECK (purpose IN ('embedding', 'translation', 'intent_rewrite', 'rerank', 'answer_generation'));

COMMENT ON COLUMN rag_model_purpose_bindings.fallback_provider_ids IS
    '按优先级从高到低排列的备用供应商 ID；运行时遇到限额、超时或不可用会依次尝试。';

COMMIT;
