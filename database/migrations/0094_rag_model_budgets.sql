-- RAG-024：模型供应商和用途级预算策略及脱敏用量摘要。
BEGIN;
CREATE TABLE IF NOT EXISTS rag_model_budget_policies (
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider_id TEXT NOT NULL REFERENCES rag_model_providers(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose IN ('embedding', 'intent_rewrite', 'rerank', 'answer_generation')),
    daily_token_limit BIGINT NOT NULL CHECK (daily_token_limit > 0),
    monthly_token_limit BIGINT NOT NULL CHECK (monthly_token_limit > 0),
    daily_request_limit INTEGER NOT NULL CHECK (daily_request_limit > 0),
    monthly_budget NUMERIC(14, 4) NOT NULL CHECK (monthly_budget >= 0),
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id, provider_id, purpose)
);

CREATE TABLE IF NOT EXISTS rag_model_budget_usage (
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider_id TEXT NOT NULL REFERENCES rag_model_providers(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose IN ('embedding', 'intent_rewrite', 'rerank', 'answer_generation')),
    period_start DATE NOT NULL,
    daily_tokens BIGINT NOT NULL DEFAULT 0 CHECK (daily_tokens >= 0),
    monthly_tokens BIGINT NOT NULL DEFAULT 0 CHECK (monthly_tokens >= 0),
    daily_requests INTEGER NOT NULL DEFAULT 0 CHECK (daily_requests >= 0),
    monthly_cost NUMERIC(14, 4) NOT NULL DEFAULT 0 CHECK (monthly_cost >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id, provider_id, purpose, period_start)
);

ALTER TABLE rag_model_budget_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_model_budget_policies FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_model_budget_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_model_budget_usage FORCE ROW LEVEL SECURITY;
CREATE POLICY rag_model_budget_policies_isolation ON rag_model_budget_policies USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));
CREATE POLICY rag_model_budget_usage_isolation ON rag_model_budget_usage USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));
COMMENT ON TABLE rag_model_budget_usage IS '按周期累计的脱敏 token、请求次数和成本摘要；不保存提示词或模型原始响应。';
COMMENT ON COLUMN rag_model_budget_policies.purpose IS '用途级预算边界；主备模型切换必须分别经过同一用途策略。';
COMMENT ON COLUMN rag_model_budget_usage.purpose IS '与策略用途一致，防止嵌入、重排和回答用量互相冲抵。';
COMMIT;
