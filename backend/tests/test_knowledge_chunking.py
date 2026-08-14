from dataclasses import replace

import pytest

from backend.app.domain.knowledge_chunking import (
    ChunkingRequest,
    ChunkMetadata,
    ChunkStrategyRegistry,
    ParsedNode,
    PdfChunkingRequest,
    PdfPage,
    RawKnowledgeDocument,
    approximate_token_count,
    assess_chunk_quality,
    build_default_chunk_registry,
)


def _metadata(
    *, source_type: str = "markdown", strategy: str = "markdown_sections"
) -> ChunkMetadata:
    return ChunkMetadata(
        document_id="doc-1",
        document_version_id="version-1",
        business_domain="requirements",
        source_type=source_type,  # type: ignore[arg-type]
        source_level="b",
        language="zh-CN",
        title_path=("RAG",),
        source_locator="docs/rag.md",
        chunk_strategy=strategy,
        chunk_strategy_version="1",
    )


def test_document_boundary_models_keep_source_and_structure() -> None:
    raw = RawKnowledgeDocument(
        document_id="doc-1",
        source_type="markdown",
        filename="rag.md",
        content="# 标题\n\n正文",
        content_hash="abc",
        language="zh-CN",
        business_domain="requirements",
    )
    node = ParsedNode(kind="paragraph", text="正文", locator="#标题", title_path=("标题",))

    assert raw.content_hash == "abc"
    assert node.title_path == ("标题",)


def test_markdown_strategy_preserves_heading_path_and_stable_id() -> None:
    registry = build_default_chunk_registry()
    request = ChunkingRequest(
        content="# 需求\n\n## 切片\n\n必须保留来源。",
        metadata=_metadata(),
    )

    first = registry.chunk(request)
    second = registry.chunk(request)

    assert len(first) == 1
    assert first[0].chunk_id == second[0].chunk_id
    assert first[0].metadata.title_path == ("RAG", "需求", "切片")
    assert first[0].metadata.source_locator == "#RAG/需求/切片"


def test_oversized_atomic_paragraph_is_split_under_hard_limit() -> None:
    registry = build_default_chunk_registry()
    metadata = _metadata()
    request = ChunkingRequest(
        content="第一个超长句子包含独特内容。" * 20 + "第二个超长句子包含不同内容。" * 20,
        metadata=metadata,
        target_tokens=50,
        max_tokens=50,
        overlap_tokens=0,
    )

    chunks = registry.chunk(request)

    assert len(chunks) > 1
    assert all(approximate_token_count(chunk.content) <= 50 for chunk in chunks)
    assert assess_chunk_quality(chunks, max_tokens=50).passed is True


def test_pdf_strategies_preserve_page_locator_and_reject_wrong_source() -> None:
    registry = build_default_chunk_registry()
    metadata = _metadata(source_type="pdf", strategy="pdf_pages")
    request = PdfChunkingRequest(
        pages=(PdfPage(page_number=3, text="第三页内容"),),
        metadata=metadata,
    )

    chunks = registry.chunk_pdf(request)

    assert chunks[0].metadata.page_from == 3
    assert chunks[0].metadata.source_locator.endswith("#page=3")
    with pytest.raises(ValueError, match="source_type"):
        registry.chunk_pdf(replace(request, metadata=_metadata()))


def test_quality_report_rejects_duplicate_and_oversized_chunks() -> None:
    registry = build_default_chunk_registry()
    metadata = _metadata()
    chunks = registry.chunk(
        ChunkingRequest(
            content="同一段落",
            metadata=metadata,
            target_tokens=50,
            max_tokens=50,
            overlap_tokens=0,
        )
    )
    duplicate = replace(chunks[0], chunk_id="duplicate")

    report = assess_chunk_quality([chunks[0], duplicate], max_tokens=1)

    assert report.duplicate_content_count == 1
    assert report.oversized_count == 2
    assert report.passed is False


def test_registry_rejects_duplicate_strategy_registration() -> None:
    registry = ChunkStrategyRegistry()
    strategy = build_default_chunk_registry()._strategies[
        ("requirements", "markdown", "markdown_sections")
    ]
    registry.register(business_domain="requirements", source_type="markdown", strategy=strategy)
    with pytest.raises(ValueError, match="已注册"):
        registry.register(business_domain="requirements", source_type="markdown", strategy=strategy)
