-- RAG-结果页：保存执行进度和脱敏指标快照，页面刷新后仍可追溯验收结论。
BEGIN;
ALTER TABLE rag_evaluation_runs
    ADD COLUMN IF NOT EXISTS executed_count INTEGER NOT NULL DEFAULT 0 CHECK (executed_count >= 0),
    ADD COLUMN IF NOT EXISTS metrics JSONB,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
COMMENT ON COLUMN rag_evaluation_runs.executed_count IS '已完成并纳入指标分母的案例数；错误、跳过和未执行不计入。';
COMMENT ON COLUMN rag_evaluation_runs.metrics IS '脱敏指标快照，只保存聚合数值和门禁结论，不保存问题、提示词或模型原文。';
COMMENT ON COLUMN rag_evaluation_runs.completed_at IS '评测完成或失败时间；排队和运行中为空。';
COMMIT;
