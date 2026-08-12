-- RAG-009：为已发布知识切片建立 PostgreSQL 关键词检索索引。
-- 正文、定位和策略字段共同参与检索，权限与发布状态仍由查询条件强制过滤。
ALTER TABLE rag_knowledge_chunks
    ADD COLUMN IF NOT EXISTS search_document tsvector
    GENERATED ALWAYS AS (
        to_tsvector(
            'simple',
            coalesce(content, '') || ' ' || coalesce(source_locator, '') || ' ' ||
            array_to_string(title_path, ' ')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_rag_chunks_search_document
    ON rag_knowledge_chunks USING GIN (search_document);

COMMENT ON COLUMN rag_knowledge_chunks.search_document IS
    '由正文、标题路径和来源定位生成的全文检索向量；只服务关键词召回，不替代 Chroma 语义向量。';
