-- RAG-023/024：模型供应商、用途主备绑定和预算摘要持久化。
BEGIN;

CREATE TABLE IF NOT EXISTS rag_model_providers (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (btrim(name) <> ''),
    adapter_type TEXT NOT NULL CHECK (adapter_type IN ('deepseek', 'minimax', 'openai', 'openai_compatible')),
    model TEXT NOT NULL CHECK (btrim(model) <> ''),
    api_key TEXT NOT NULL CHECK (btrim(api_key) <> ''),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 100 CHECK (priority > 0),
    credential_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_model_purpose_bindings (
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose IN ('embedding', 'intent_rewrite', 'rerank', 'answer_generation')),
    primary_provider_id TEXT NOT NULL REFERENCES rag_model_providers(id) ON DELETE RESTRICT,
    fallback_provider_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id, purpose)
);

CREATE INDEX IF NOT EXISTS idx_rag_model_providers_priority
    ON rag_model_providers (organization_id, enabled, priority);

ALTER TABLE rag_model_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_model_providers FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_model_purpose_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_model_purpose_bindings FORCE ROW LEVEL SECURITY;
CREATE POLICY rag_model_providers_isolation ON rag_model_providers USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));
CREATE POLICY rag_model_purpose_bindings_isolation ON rag_model_purpose_bindings USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));

COMMENT ON COLUMN rag_model_providers.api_key IS '供应商 API Key；仅服务端写入和运行时读取，任何 API 响应、日志和追踪均不得回显。';
COMMENT ON COLUMN rag_model_purpose_bindings.fallback_provider_ids IS '按优先级排列的备用供应商 ID；必须经过能力和配额门禁。';
COMMIT;
