-- 知识型混合 RAG 首期治理结构。
-- PostgreSQL 保存知识事实、生命周期和任务状态；Chroma 仅保存可重建的向量索引。
-- 本迁移只建立 RAG-2 所需的最小关系模型，不写入真实知识正文或凭据。

BEGIN;

CREATE TABLE IF NOT EXISTS rag_knowledge_sources (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    source_type TEXT NOT NULL CHECK (source_type IN ('markdown', 'postgres_schema', 'pdf')),
    business_domain TEXT NOT NULL,
    title TEXT NOT NULL CHECK (btrim(title) <> ''),
    authority_level TEXT NOT NULL CHECK (authority_level IN ('a', 'b', 'c')),
    sensitivity TEXT NOT NULL DEFAULT 'internal'
        CHECK (sensitivity IN ('public', 'internal', 'restricted')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'withdrawn', 'deleted')),
    source_locator TEXT NOT NULL CHECK (btrim(source_locator) <> ''),
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    UNIQUE (organization_id, source_locator)
);

CREATE TABLE IF NOT EXISTS rag_document_versions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    content_hash TEXT NOT NULL CHECK (btrim(content_hash) <> ''),
    parser_name TEXT NOT NULL CHECK (btrim(parser_name) <> ''),
    parser_version TEXT NOT NULL CHECK (btrim(parser_version) <> ''),
    cleaner_version TEXT NOT NULL CHECK (btrim(cleaner_version) <> ''),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'processing', 'published', 'withdrawn', 'deleted')),
    effective_from TIMESTAMPTZ,
    effective_to TIMESTAMPTZ,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ,
    UNIQUE (source_id, version_number),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, source_id)
        REFERENCES rag_knowledge_sources (organization_id, id) ON DELETE RESTRICT,
    CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_rag_published_version_per_source
    ON rag_document_versions (source_id)
    WHERE status = 'published';
CREATE INDEX IF NOT EXISTS idx_rag_versions_scope_status
    ON rag_document_versions (organization_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS rag_knowledge_chunks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    document_version_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    parent_chunk_id TEXT,
    content TEXT NOT NULL CHECK (btrim(content) <> ''),
    content_hash TEXT NOT NULL CHECK (btrim(content_hash) <> ''),
    source_locator TEXT NOT NULL CHECK (btrim(source_locator) <> ''),
    title_path TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    language TEXT NOT NULL CHECK (btrim(language) <> ''),
    chunk_strategy TEXT NOT NULL CHECK (btrim(chunk_strategy) <> ''),
    chunk_strategy_version TEXT NOT NULL CHECK (btrim(chunk_strategy_version) <> ''),
    page_from INTEGER CHECK (page_from IS NULL OR page_from > 0),
    page_to INTEGER CHECK (page_to IS NULL OR page_to >= page_from),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'indexing', 'published', 'withdrawn', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_version_id, ordinal),
    FOREIGN KEY (organization_id, document_version_id)
        REFERENCES rag_document_versions (organization_id, id) ON DELETE CASCADE,
    FOREIGN KEY (parent_chunk_id) REFERENCES rag_knowledge_chunks (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_retrieval
    ON rag_knowledge_chunks (organization_id, status, document_version_id, ordinal);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_hash
    ON rag_knowledge_chunks (organization_id, content_hash);

CREATE TABLE IF NOT EXISTS rag_ingestion_jobs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL,
    document_version_id TEXT,
    job_type TEXT NOT NULL CHECK (job_type IN ('ingest', 'index', 'withdraw', 'delete', 'rebuild')),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    idempotency_key TEXT NOT NULL CHECK (btrim(idempotency_key) <> ''),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    error_code TEXT,
    error_summary TEXT,
    lease_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    UNIQUE (organization_id, idempotency_key),
    FOREIGN KEY (organization_id, source_id)
        REFERENCES rag_knowledge_sources (organization_id, id) ON DELETE RESTRICT,
    FOREIGN KEY (document_version_id)
        REFERENCES rag_document_versions (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_rag_jobs_dispatch
    ON rag_ingestion_jobs (organization_id, status, created_at);

ALTER TABLE rag_knowledge_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_knowledge_sources FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_document_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_knowledge_chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE rag_ingestion_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_ingestion_jobs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rag_knowledge_sources_isolation ON rag_knowledge_sources;
CREATE POLICY rag_knowledge_sources_isolation ON rag_knowledge_sources
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
DROP POLICY IF EXISTS rag_document_versions_isolation ON rag_document_versions;
CREATE POLICY rag_document_versions_isolation ON rag_document_versions
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
DROP POLICY IF EXISTS rag_knowledge_chunks_isolation ON rag_knowledge_chunks;
CREATE POLICY rag_knowledge_chunks_isolation ON rag_knowledge_chunks
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));
DROP POLICY IF EXISTS rag_ingestion_jobs_isolation ON rag_ingestion_jobs;
CREATE POLICY rag_ingestion_jobs_isolation ON rag_ingestion_jobs
    USING (organization_id = current_setting('app.organization_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true));

COMMENT ON TABLE rag_knowledge_sources IS 'RAG 知识来源目录；记录来源类型、业务域、权威级别和生命周期，不保存凭据。';
COMMENT ON TABLE rag_document_versions IS 'RAG 文档版本事实；每个来源可有多个版本，但同一来源最多一个已发布版本。';
COMMENT ON TABLE rag_knowledge_chunks IS 'RAG 文档切片目录；保存正文哈希、结构定位、策略版本和索引生命周期。';
COMMENT ON TABLE rag_ingestion_jobs IS 'RAG 摄取与索引任务事实；Redis 只发送任务 ID，任务状态以本表为准。';

COMMENT ON COLUMN rag_knowledge_sources.source_type IS '来源类型；首期仅允许 Markdown、PostgreSQL 结构语料和文本层 PDF。';
COMMENT ON COLUMN rag_knowledge_sources.business_domain IS '知识业务域；用于选择切片策略和查询过滤。';
COMMENT ON COLUMN rag_knowledge_sources.authority_level IS '知识权威级别；A/B/C 决定冲突处理和高风险回答可用性。';
COMMENT ON COLUMN rag_knowledge_sources.source_locator IS '来源定位；保存受控路径或结构标识，不保存凭据。';
COMMENT ON COLUMN rag_document_versions.version_number IS '同一来源的递增版本号；用于发布、撤回和历史引用。';
COMMENT ON COLUMN rag_document_versions.content_hash IS '清洗前后版本对账哈希；用于幂等摄取和变更检测。';
COMMENT ON COLUMN rag_document_versions.status IS '版本生命周期；同一来源只能存在一个 published 版本。';
COMMENT ON COLUMN rag_knowledge_chunks.ordinal IS '切片在文档版本内的稳定顺序号，从零开始。';
COMMENT ON COLUMN rag_knowledge_chunks.content IS '清洗后的可检索正文；不得包含凭据、客户隐私或禁止进入 RAG 的值。';
COMMENT ON COLUMN rag_knowledge_chunks.content_hash IS '切片正文 SHA-256 哈希；用于重复检测和 Chroma 对账。';
COMMENT ON COLUMN rag_knowledge_chunks.source_locator IS '切片引用定位；可包含 Markdown 路径、字段标识或 PDF 页码。';
COMMENT ON COLUMN rag_knowledge_chunks.title_path IS '从文档根到当前结构节点的标题路径；用于上下文和引用展示。';
COMMENT ON COLUMN rag_knowledge_chunks.chunk_strategy IS '切片策略名称；必须与版本化策略注册表一致。';
COMMENT ON COLUMN rag_knowledge_chunks.chunk_strategy_version IS '切片策略版本；变更后必须生成新索引版本。';
COMMENT ON COLUMN rag_knowledge_chunks.status IS '切片索引生命周期；withdrawn/deleted 切片不得进入召回。';
COMMENT ON COLUMN rag_ingestion_jobs.job_type IS '摄取、索引、撤回、删除或重建任务类型。';
COMMENT ON COLUMN rag_ingestion_jobs.idempotency_key IS '任务幂等键；同一组织内重复提交不得产生多个任务。';
COMMENT ON COLUMN rag_ingestion_jobs.attempt_count IS 'Worker 尝试次数；用于租约接管、退避和死信判定。';
COMMENT ON COLUMN rag_ingestion_jobs.error_summary IS '脱敏错误摘要；不得写入 API Key、正文或客户数据。';

COMMIT;
