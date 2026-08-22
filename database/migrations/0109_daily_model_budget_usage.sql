-- RAG-024 修复：用量的 daily_* 字段必须按 Asia/Shanghai 自然日隔离。
-- 旧实现把 period_start 固定为月初，导致同月不同日期累计到同一行并被误显示为今日用量。
BEGIN;

CREATE INDEX IF NOT EXISTS rag_model_budget_usage_period_lookup
    ON rag_model_budget_usage (organization_id, provider_id, purpose, period_start);

COMMENT ON COLUMN rag_model_budget_usage.period_start IS
    'Asia/Shanghai 自然日日期键；daily_* 只属于该日期，monthly_* 由当前自然月日期行汇总。';

COMMIT;
