"""知识接入流水线的端到端领域测试。"""

from backend.app.domain.knowledge_pipeline import ingest_and_chunk


def test_markdown_pipeline_returns_publishable_draft_chunks() -> None:
    result = ingest_and_chunk(
        document_id="d1", document_version_id="v1", source_type="markdown",
        business_domain="sop", filename="sop.md", content="# 库存\n\n同步失败检查任务状态。",
        strategy="markdown_sections", source_locator="docs/sop.md",
    )
    assert result.parser_name == "markdown_parser"
    assert result.chunks[0].metadata.status == "draft"
    assert result.quality_passed is True


def test_pdf_pipeline_keeps_page_locator() -> None:
    result = ingest_and_chunk(
        document_id="d2", document_version_id="v2", source_type="pdf",
        business_domain="sop", filename="sop.pdf", content="第一页内容\f第二页内容",
        strategy="pdf_pages", source_locator="uploads/sop.pdf",
    )
    assert result.chunks[1].metadata.page_from == 2
