-- RAG-027/025/028：查询追踪、反馈、评测案例和试运行开关的持久化事实。
BEGIN;

CREATE TABLE IF NOT EXISTS rag_query_traces (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id TEXT,
    question_hash TEXT NOT NULL,
    retrieval_policy_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('answered', 'partially_answered', 'unsupported', 'refused', 'degraded')),
    segment_count INTEGER NOT NULL CHECK (segment_count >= 0),
    citation_count INTEGER NOT NULL CHECK (citation_count >= 0),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_feedback (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    answer_id TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('helpful', 'incorrect', 'outdated_source', 'missing_answer', 'citation_mismatch')),
    note TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'dismissed')),
    resolution_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS rag_evaluation_cases (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    question TEXT NOT NULL CHECK (btrim(question) <> ''),
    expected_status TEXT NOT NULL,
    expected_sources TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    safety_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'confirmed', 'rejected')),
    reviewer_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS rag_evaluation_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    suite TEXT NOT NULL CHECK (suite IN ('quick', 'standard', 'full')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    gate_status TEXT NOT NULL CHECK (gate_status IN ('ready', 'blocked')),
    passed_count INTEGER NOT NULL DEFAULT 0 CHECK (passed_count >= 0),
    failed_count INTEGER NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
    error_count INTEGER NOT NULL DEFAULT 0 CHECK (error_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_rollout_flags (
    name TEXT NOT NULL,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('disabled', 'shadow', 'pilot', 'internal')),
    pilot_until TIMESTAMPTZ,
    reason TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id, name)
);

CREATE INDEX IF NOT EXISTS idx_rag_traces_scope_time ON rag_query_traces (organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rag_feedback_scope_status ON rag_feedback (organization_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rag_eval_cases_scope_status ON rag_evaluation_cases (organization_id, status, created_at DESC);

ALTER TABLE rag_query_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_query_traces FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_feedback FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_evaluation_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_evaluation_cases FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_evaluation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_evaluation_runs FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_rollout_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_rollout_flags FORCE ROW LEVEL SECURITY;

CREATE POLICY rag_query_traces_isolation ON rag_query_traces USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));
CREATE POLICY rag_feedback_isolation ON rag_feedback USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));
CREATE POLICY rag_evaluation_cases_isolation ON rag_evaluation_cases USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));
CREATE POLICY rag_evaluation_runs_isolation ON rag_evaluation_runs USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));
CREATE POLICY rag_rollout_flags_isolation ON rag_rollout_flags USING (organization_id = current_setting('app.organization_id', true)) WITH CHECK (organization_id = current_setting('app.organization_id', true));

COMMENT ON TABLE rag_query_traces IS 'RAG 查询脱敏追踪摘要；不保存完整问题、提示词或模型原始响应。';
COMMENT ON TABLE rag_feedback IS '用户反馈和人工处理状态；反馈不能直接修改知识正文。';
COMMENT ON TABLE rag_evaluation_cases IS 'AI 辅助生成、人工确认后的 RAG 评测案例。';
COMMENT ON TABLE rag_evaluation_runs IS 'RAG 评测运行结果聚合，不允许未通过门禁的运行伪装为通过。';
COMMENT ON TABLE rag_rollout_flags IS '组织级 RAG 功能开关和试运行期限。';
COMMIT;
