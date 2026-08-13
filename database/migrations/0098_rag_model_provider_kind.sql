-- RAG-025：区分向量模型池与文本模型池，避免管理页面和运行时把两类能力混用。
BEGIN;

ALTER TABLE rag_model_providers
    ADD COLUMN IF NOT EXISTS model_kind TEXT NOT NULL DEFAULT 'text';

ALTER TABLE rag_model_providers
    DROP CONSTRAINT IF EXISTS rag_model_providers_model_kind_check;
ALTER TABLE rag_model_providers
    ADD CONSTRAINT rag_model_providers_model_kind_check
    CHECK (model_kind IN ('embedding', 'text'));

COMMENT ON COLUMN rag_model_providers.model_kind IS
    '模型能力池：embedding 表示向量化模型，text 表示翻译、意图重写、重排和回答模型；管理与运行时不得跨池调用。';

CREATE INDEX IF NOT EXISTS idx_rag_model_providers_kind_priority
    ON rag_model_providers (organization_id, model_kind, enabled, priority, id);

COMMIT;
