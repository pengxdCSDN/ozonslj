-- SEL-007：同一工作区的利润模型假设按保存顺序递增版本，便于复盘输入口径变化。
BEGIN;
ALTER TABLE profit_models ADD COLUMN IF NOT EXISTS assumption_version INTEGER;
UPDATE profit_models SET assumption_version = 1 WHERE assumption_version IS NULL;
ALTER TABLE profit_models ALTER COLUMN assumption_version SET NOT NULL;
ALTER TABLE profit_models ALTER COLUMN assumption_version SET DEFAULT 1;
CREATE UNIQUE INDEX IF NOT EXISTS uq_profit_models_workspace_version
    ON profit_models (workspace_id, assumption_version);
COMMIT;
