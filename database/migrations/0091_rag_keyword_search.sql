-- RAG-009：为已发布知识切片建立 PostgreSQL 关键词检索索引。
-- 正文、定位和策略字段共同参与检索，权限与发布状态仍由查询条件强制过滤。

-- PostgreSQL 不允许使用稳定函数构造 generated column；改用普通 tsvector 列和
-- 行级触发器，既保持可索引的物化结果，又能在正文、来源定位或标题路径更新时同步。
-- 该迁移之前可能已创建过失败的 generated column，因此先删除该迁移拥有的列再重建，
-- 不影响业务事实表，且保证重试路径结构确定。
ALTER TABLE rag_knowledge_chunks DROP COLUMN IF EXISTS search_document;
ALTER TABLE rag_knowledge_chunks ADD COLUMN search_document tsvector;

CREATE OR REPLACE FUNCTION rag_refresh_chunk_search_document()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_document := to_tsvector(
        'simple'::regconfig,
        coalesce(NEW.content, '') || ' ' || coalesce(NEW.source_locator, '') || ' ' ||
        array_to_string(NEW.title_path, ' ')
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rag_refresh_chunk_search_document ON rag_knowledge_chunks;
CREATE TRIGGER trg_rag_refresh_chunk_search_document
    BEFORE INSERT OR UPDATE OF content, source_locator, title_path
    ON rag_knowledge_chunks
    FOR EACH ROW
    EXECUTE FUNCTION rag_refresh_chunk_search_document();

UPDATE rag_knowledge_chunks
SET search_document = to_tsvector(
    'simple'::regconfig,
    coalesce(content, '') || ' ' || coalesce(source_locator, '') || ' ' ||
    array_to_string(title_path, ' ')
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_search_document
    ON rag_knowledge_chunks USING GIN (search_document);

COMMENT ON COLUMN rag_knowledge_chunks.search_document IS
    '由正文、标题路径和来源定位物化生成的全文检索向量；只服务关键词召回，不替代 Chroma 语义向量。';
