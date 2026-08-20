"""PostgreSQL RAG 关键词检索适配器，负责精确信号和全文召回。"""

from __future__ import annotations

from typing import Literal, cast

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_retrieval import KeywordSearchPort, RetrievalHit


class PostgresKnowledgeKeywordSearch(KeywordSearchPort):
    """只返回当前组织、已发布版本和已发布切片，避免草稿或撤回内容泄漏到 RAG。"""

    def __init__(self, pool: AsyncConnectionPool, organization_id: str) -> None:
        """初始化对象依赖和运行时状态。

Args:
    pool: 参数语义、输入边界和安全约束。
    organization_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
        if not organization_id.strip():
            raise ValueError("organization_id 不能为空")
        self._pool = pool
        self._organization_id = organization_id

    async def search(self, query: str, *, limit: int) -> list[RetrievalHit]:
        """执行 search 的业务流程并返回该流程的结果。

Args:
    query: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        if not query.strip() or limit < 1:
            return []
        bounded_limit = min(limit, 50)
        async with self._pool.connection() as connection, connection.cursor(
            row_factory=dict_row
        ) as cursor:
            # 连接池会复用物理连接，必须在每次查询前设置 RLS 组织上下文。
            await connection.execute(
                "SELECT set_config('app.organization_id', %s, true)",
                (self._organization_id,),
            )
            await cursor.execute(
                """
                SELECT c.id, c.content, c.content_hash, c.ordinal,
                       c.document_version_id, v.source_id, c.language,
                       c.source_locator, c.title_path, c.chunk_strategy,
                       c.chunk_strategy_version, c.page_from, c.page_to,
                       c.status, s.business_domain, s.source_type,
                       s.authority_level, s.sensitivity
                FROM rag_knowledge_chunks AS c
                JOIN rag_document_versions AS v ON v.id = c.document_version_id
                JOIN rag_knowledge_sources AS s ON s.id = v.source_id
                WHERE c.organization_id = %s
                  AND c.status = 'published'
                  AND v.status = 'published'
                  AND s.status = 'active'
                  AND c.search_document @@ plainto_tsquery('simple', %s)
                ORDER BY ts_rank_cd(c.search_document, plainto_tsquery('simple', %s)) DESC,
                         c.id ASC
                LIMIT %s
                """,
                (self._organization_id, query, query, bounded_limit),
            )
            rows = await cursor.fetchall()
        return [_hit_from_row(row) for row in rows]


def _hit_from_row(row: dict[str, object]) -> RetrievalHit:
    """执行内部步骤 _hit_from_row，供同一模块的公开流程复用。

Args:
    row: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    source_type = cast(Literal["markdown", "postgres_schema", "pdf"], str(row["source_type"]))
    business_domain = cast(
        Literal[
            "domain_language", "requirements", "architecture", "api", "database", "sop",
            "troubleshooting", "ozon_official", "general",
        ], str(row["business_domain"])
    )
    source_level = cast(Literal["a", "b", "c"], str(row["authority_level"]))
    sensitivity = cast(Literal["public", "internal", "restricted"], str(row["sensitivity"]))
    title_path_value = row["title_path"]
    title_path = (
        tuple(str(item) for item in title_path_value)
        if isinstance(title_path_value, list)
        else ()
    )
    metadata = ChunkMetadata(
        document_id=str(row["source_id"]), document_version_id=str(row["document_version_id"]),
        business_domain=business_domain, source_type=source_type, source_level=source_level,
        language=str(row["language"]), title_path=title_path,
        source_locator=str(row["source_locator"]), chunk_strategy=str(row["chunk_strategy"]),
        chunk_strategy_version=str(row["chunk_strategy_version"]), status="published",
        sensitivity=sensitivity, page_from=_optional_int(row["page_from"]),
        page_to=_optional_int(row["page_to"]),
    )
    chunk = KnowledgeChunk(
        str(row["id"]), str(row["content"]), str(row["content_hash"]),
        int(str(row["ordinal"])), metadata,
    )
    return RetrievalHit(chunk, 1.0, "keyword")


def _optional_int(value: object) -> int | None:
    """执行内部步骤 _optional_int，供同一模块的公开流程复用。

Args:
    value: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return int(str(value)) if value is not None else None
