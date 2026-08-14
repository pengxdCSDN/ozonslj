-- RAG-025：重排序模型属于独立能力池，必须与 Embedding、文本模型分开校验，避免保存配置时被旧约束拒绝。
BEGIN;

ALTER TABLE rag_model_providers
    DROP CONSTRAINT IF EXISTS rag_model_providers_model_kind_check;
ALTER TABLE rag_model_providers
    ADD CONSTRAINT rag_model_providers_model_kind_check
    CHECK (model_kind IN ('embedding', 'rerank', 'text'));

COMMENT ON COLUMN rag_model_providers.model_kind IS
    '模型能力类型：embedding 向量化、rerank 重排序、text 翻译/意图重写/答案生成；用途绑定只能选择同类型模型。';

COMMIT;
