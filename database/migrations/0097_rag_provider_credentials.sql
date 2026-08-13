-- RAG-023：供应商 API Key 由受限凭据目录管理；PostgreSQL 只保存引用和末尾掩码。
BEGIN;

ALTER TABLE rag_model_providers
    ADD COLUMN IF NOT EXISTS credential_ref TEXT,
    ADD COLUMN IF NOT EXISTS credential_suffix TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE rag_model_providers
    DROP CONSTRAINT IF EXISTS rag_model_providers_api_key_check;
ALTER TABLE rag_model_providers
    ALTER COLUMN api_key DROP NOT NULL;

UPDATE rag_model_providers
SET credential_suffix = right(api_key, 4)
WHERE credential_suffix IS NULL AND api_key IS NOT NULL AND btrim(api_key) <> '';

COMMENT ON COLUMN rag_model_providers.api_key IS
    '历史兼容列；新配置不得写入 API Key，凭据必须写入受限文件并通过 credential_ref 引用。';
COMMENT ON COLUMN rag_model_providers.credential_ref IS
    '供应商凭据文件引用；仅允许服务端解析，任何 API 响应不得回显绝对路径。';
COMMENT ON COLUMN rag_model_providers.credential_suffix IS
    'API Key 末四位掩码，仅用于管理员确认当前凭据，不是可用凭据。';

COMMIT;
