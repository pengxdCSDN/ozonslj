"""知识接入到切片质量门禁的统一编排。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256

from backend.app.domain.knowledge_chunking import (
    BusinessDomain,
    ChunkingRequest,
    ChunkMetadata,
    KnowledgeChunk,
    PdfChunkingRequest,
    PdfPage,
    RawKnowledgeDocument,
    SourceType,
    assess_chunk_quality,
    build_default_chunk_registry,
)
from backend.app.domain.knowledge_ingestion import clean_knowledge_document, parser_for


@dataclass(frozen=True, slots=True)
class KnowledgePipelineResult:
    """说明 KnowledgePipelineResult 的职责、状态边界和对外协作关系。"""
    document_id: str
    document_version_id: str
    parser_name: str
    cleaner_version: str
    content_hash: str
    chunks: tuple[KnowledgeChunk, ...]
    quality_passed: bool
    blocked_reason: str | None


def ingest_and_chunk(
    *,
    document_id: str,
    document_version_id: str,
    source_type: SourceType,
    business_domain: BusinessDomain,
    filename: str,
    content: str,
    strategy: str,
    source_locator: str,
    max_tokens: int = 520,
    overlap_tokens: int = 60,
) -> KnowledgePipelineResult:
    """执行解析、清洗、切片和质量门禁；门禁失败时仍返回草稿切片但禁止发布。

Args:
    document_id: 参数语义、输入边界和安全约束。
    document_version_id: 参数语义、输入边界和安全约束。
    source_type: 参数语义、输入边界和安全约束。
    business_domain: 参数语义、输入边界和安全约束。
    filename: 参数语义、输入边界和安全约束。
    content: 参数语义、输入边界和安全约束。
    strategy: 参数语义、输入边界和安全约束。
    source_locator: 参数语义、输入边界和安全约束。
    max_tokens: 参数语义、输入边界和安全约束。
    overlap_tokens: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    raw = RawKnowledgeDocument(
        document_id=document_id, source_type=source_type, filename=filename,
        content=content, content_hash=sha256(content.encode("utf-8")).hexdigest(),
        language="zh-CN", business_domain=business_domain,
    )
    parsed = parser_for(source_type).parse(raw, document_version_id=document_version_id)
    cleaned = clean_knowledge_document(parsed)
    metadata = ChunkMetadata(
        document_id=document_id, document_version_id=document_version_id,
        business_domain=business_domain, source_type=source_type, source_level="c",
        language=raw.language, title_path=(), source_locator=source_locator,
        chunk_strategy=strategy, chunk_strategy_version="1", status="draft",
    )
    registry = build_default_chunk_registry()
    if source_type == "pdf":
        pages = tuple(
            PdfPage(node.page_from or index, node.text)
            for index, node in enumerate(cleaned.nodes, start=1)
        )
        chunks = registry.chunk_pdf(
            PdfChunkingRequest(
                pages=pages, metadata=metadata, max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
            )
        )
    else:
        chunks = registry.chunk(
            ChunkingRequest(
                content="\n\n".join(node.text for node in cleaned.nodes), metadata=metadata,
                max_tokens=max_tokens, overlap_tokens=overlap_tokens,
            )
        )
    # 对外引用统一返回文档级定位；结构锚点保存在 extra，避免前端只看到
    # ``#document`` 等解析器内部定位而无法回到原始文件。
    chunks = [
        replace(
            chunk,
            metadata=replace(
                chunk.metadata,
                source_locator=source_locator,
                extra=(*chunk.metadata.extra, ("section_locator", chunk.metadata.source_locator)),
            ),
        )
        for chunk in chunks
    ]
    quality = assess_chunk_quality(chunks, max_tokens=max_tokens)
    return KnowledgePipelineResult(
        document_id=document_id, document_version_id=document_version_id,
        parser_name=parsed.parser_name, cleaner_version=cleaned.cleaner_version,
        content_hash=cleaned.content_hash, chunks=tuple(chunks),
        quality_passed=quality.passed,
        blocked_reason=None if quality.passed else "切片质量门禁未通过",
    )
