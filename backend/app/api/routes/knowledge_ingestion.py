"""知识接入流水线 API；只返回脱敏切片摘要和质量门禁。"""

from __future__ import annotations

from typing import Literal, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.knowledge_pipeline import ingest_and_chunk
from backend.app.domain.knowledge_runtime import get_knowledge_runtime, stage_knowledge_chunks

router = APIRouter(prefix="/v1/knowledge-ingestion", tags=["knowledge-ingestion"])


class IngestionPayload(BaseModel):
    """说明 IngestionPayload 的职责、状态边界和对外协作关系。"""
    document_id: str = Field(default="api-document", min_length=1, max_length=100)
    document_version_id: str = Field(default="api-version", min_length=1, max_length=100)
    source_type: str = Field(pattern="^(markdown|postgres_schema|pdf)$")
    business_domain: str = Field(min_length=1, max_length=40)
    filename: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=500_000)
    strategy: str = Field(min_length=1, max_length=60)
    source_locator: str = Field(min_length=1, max_length=500)
    max_tokens: int = Field(default=520, ge=50, le=2_000)
    overlap_tokens: int = Field(default=60, ge=0, le=500)


class IngestionResponse(BaseModel):
    """说明 IngestionResponse 的职责、状态边界和对外协作关系。"""
    document_id: str
    document_version_id: str
    parser_name: str
    cleaner_version: str
    content_hash: str
    quality_passed: bool
    blocked_reason: str | None
    chunks: list[dict[str, object]]


@router.post("/run", response_model=IngestionResponse)
async def run_knowledge_ingestion(payload: IngestionPayload) -> IngestionResponse:
    """执行 run_knowledge_ingestion 的业务流程并返回该流程的结果。"""
    try:
        result = ingest_and_chunk(
            document_id=payload.document_id, document_version_id=payload.document_version_id,
            source_type=cast(Literal["markdown", "postgres_schema", "pdf"], payload.source_type),
            business_domain=cast(
                Literal[
                    "domain_language", "requirements", "architecture", "api", "database", "sop",
                    "troubleshooting", "ozon_official", "general",
                ], payload.business_domain
            ),
            filename=payload.filename, content=payload.content, strategy=payload.strategy,
            source_locator=payload.source_locator, max_tokens=payload.max_tokens,
            overlap_tokens=payload.overlap_tokens,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result.quality_passed:
        await stage_knowledge_chunks(
            get_knowledge_runtime(), result.document_version_id, result.chunks
        )
    return IngestionResponse(
        document_id=result.document_id, document_version_id=result.document_version_id,
        parser_name=result.parser_name, cleaner_version=result.cleaner_version,
        content_hash=result.content_hash, quality_passed=result.quality_passed,
        blocked_reason=result.blocked_reason,
        chunks=[
            {
                "chunk_id": chunk.chunk_id, "ordinal": chunk.ordinal,
                "source_locator": chunk.metadata.source_locator,
                "title_path": list(chunk.metadata.title_path), "content": chunk.content,
            }
            for chunk in result.chunks
        ],
    )
