-- RAG-026：允许登记云端供应商的受控 API 地址，支持 DashScope Embedding/翻译。
-- 地址只作为服务端配置使用；客户端不得在查询请求中提交地址或凭据。
BEGIN;

ALTER TABLE rag_model_providers
    DROP CONSTRAINT IF EXISTS rag_model_providers_adapter_type_check;
ALTER TABLE rag_model_providers
    ADD CONSTRAINT rag_model_providers_adapter_type_check
    CHECK (adapter_type IN ('dashscope', 'deepseek', 'minimax', 'openai', 'openai_compatible'));

ALTER TABLE rag_model_providers
    ADD COLUMN IF NOT EXISTS base_url TEXT;

ALTER TABLE rag_model_providers
    ADD CONSTRAINT rag_model_providers_base_url_check
    CHECK (base_url IS NULL OR btrim(base_url) <> '');

COMMENT ON COLUMN rag_model_providers.base_url IS
    '供应商 OpenAI-compatible API 基地址；服务端需额外执行 HTTPS、域名和重定向安全校验。';

COMMIT;
