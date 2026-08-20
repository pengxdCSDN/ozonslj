"""多策略切片预览与质量门禁 API。"""

from __future__ import annotations

from typing import Literal, cast

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.domain.knowledge_chunking import (
    ChunkingRequest,
    ChunkMetadata,
    PdfChunkingRequest,
    PdfPage,
    assess_chunk_quality,
    build_default_chunk_registry,
)

router = APIRouter(prefix="/v1/knowledge-chunk-previews", tags=["knowledge-chunking"])
_registry = build_default_chunk_registry()


class PdfPagePayload(BaseModel):
    """说明 PdfPagePayload 的职责、状态边界和对外协作关系。"""
    page_number: int = Field(ge=1)
    text: str = Field(max_length=100_000)
    layout_blocks: list[str] = Field(default_factory=list)


class ChunkPreviewPayload(BaseModel):
    """说明 ChunkPreviewPayload 的职责、状态边界和对外协作关系。"""
    source_type: str = Field(pattern="^(markdown|postgres_schema|pdf)$")
    business_domain: str = Field(min_length=1, max_length=40)
    strategy: str = Field(min_length=1, max_length=60)
    content: str = Field(default="", max_length=500_000)
    pages: list[PdfPagePayload] = Field(default_factory=list, max_length=300)
    source_locator: str = Field(min_length=1, max_length=500)
    title_path: list[str] = Field(default_factory=list, max_length=20)
    max_tokens: int = Field(default=520, ge=50, le=2_000)
    overlap_tokens: int = Field(default=60, ge=0, le=500)


class ChunkPreviewItem(BaseModel):
    """说明 ChunkPreviewItem 的职责、状态边界和对外协作关系。"""
    chunk_id: str
    content: str
    ordinal: int
    source_locator: str
    title_path: list[str]
    page_from: int | None
    page_to: int | None


class ChunkPreviewResponse(BaseModel):
    """说明 ChunkPreviewResponse 的职责、状态边界和对外协作关系。"""
    strategy: str
    strategy_version: str
    chunks: list[ChunkPreviewItem]
    quality: dict[str, object]


@router.post("", response_model=ChunkPreviewResponse)
async def preview_knowledge_chunks(payload: ChunkPreviewPayload) -> ChunkPreviewResponse:
    """执行 preview_knowledge_chunks 的业务流程并返回该流程的结果。"""
    metadata = ChunkMetadata(
        document_id="preview-document", document_version_id="preview-version",
        business_domain=cast(Literal[
            "domain_language", "requirements", "architecture", "api", "database", "sop",
            "troubleshooting", "ozon_official", "general",
        ], payload.business_domain),
        source_type=cast(Literal["markdown", "postgres_schema", "pdf"], payload.source_type),
        source_level="c", language="zh-CN", title_path=tuple(payload.title_path),
        source_locator=payload.source_locator, chunk_strategy=payload.strategy,
        chunk_strategy_version="1", status="draft",
    )
    if payload.source_type == "pdf":
        chunks = _registry.chunk_pdf(
            PdfChunkingRequest(
                pages=tuple(
                    PdfPage(page.page_number, page.text, tuple(page.layout_blocks))
                    for page in payload.pages
                ),
                metadata=metadata, max_tokens=payload.max_tokens,
                overlap_tokens=payload.overlap_tokens,
            )
        )
    else:
        chunks = _registry.chunk(
            ChunkingRequest(
                content=payload.content, metadata=metadata, max_tokens=payload.max_tokens,
                overlap_tokens=payload.overlap_tokens,
            )
        )
    strategy_version = chunks[0].metadata.chunk_strategy_version if chunks else "1"
    quality = assess_chunk_quality(chunks, max_tokens=payload.max_tokens)
    return ChunkPreviewResponse(
        strategy=payload.strategy, strategy_version=strategy_version,
        chunks=[
            ChunkPreviewItem(
                chunk_id=chunk.chunk_id, content=chunk.content, ordinal=chunk.ordinal,
                source_locator=chunk.metadata.source_locator,
                title_path=list(chunk.metadata.title_path),
                page_from=chunk.metadata.page_from, page_to=chunk.metadata.page_to,
            )
            for chunk in chunks
        ],
        quality={
            "chunk_count": quality.chunk_count, "empty_count": quality.empty_count,
            "oversized_count": quality.oversized_count,
            "duplicate_content_count": quality.duplicate_content_count,
            "missing_locator_count": quality.missing_locator_count, "passed": quality.passed,
        },
    )
