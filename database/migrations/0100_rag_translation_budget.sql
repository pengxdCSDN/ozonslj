-- 翻译与问答一样属于受控模型调用，必须拥有独立预算，不能与 Embedding 用量互相冲抵。
ALTER TABLE rag_model_budget_policies DROP CONSTRAINT IF EXISTS rag_model_budget_policies_purpose_check;
ALTER TABLE rag_model_budget_policies
    ADD CONSTRAINT rag_model_budget_policies_purpose_check
    CHECK (purpose IN ('embedding', 'translation', 'intent_rewrite', 'rerank', 'answer_generation'));
ALTER TABLE rag_model_budget_usage DROP CONSTRAINT IF EXISTS rag_model_budget_usage_purpose_check;
ALTER TABLE rag_model_budget_usage
    ADD CONSTRAINT rag_model_budget_usage_purpose_check
    CHECK (purpose IN ('embedding', 'translation', 'intent_rewrite', 'rerank', 'answer_generation'));
COMMENT ON CONSTRAINT rag_model_budget_policies_purpose_check ON rag_model_budget_policies IS
    '模型用途必须隔离；翻译、重排、回答和向量化分别计算预算。';
