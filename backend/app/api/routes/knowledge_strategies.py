"""受控切片策略注册表查询接口。"""

from fastapi import APIRouter

from backend.app.domain.knowledge_chunking import build_default_chunk_registry

router = APIRouter(prefix="/v1/knowledge-chunk-strategies", tags=["knowledge-chunking"])


@router.get("")
async def list_knowledge_chunk_strategies(
    source_type: str | None = None, business_domain: str | None = None
) -> list[dict[str, object]]:
    """只返回服务端注册策略及参数边界，不接受客户端上传代码或模块路径。

Args:
    source_type: 参数语义、输入边界和安全约束。
    business_domain: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    registry = build_default_chunk_registry()
    strategies: list[dict[str, object]] = []
    if source_type in (None, "markdown"):
        strategies.append({
            "name": "markdown_sections", "version": "1", "source_type": "markdown",
            "business_domains": ["requirements", "architecture", "api", "sop", "general"],
            "parameters": {
                "max_tokens": {"min": 50, "max": 2000},
                "overlap_tokens": {"min": 0, "max": 500},
            },
        })
    if source_type in (None, "postgres_schema") and business_domain in (None, "database"):
        strategies.append({
            "name": "postgres_table_fields", "version": "1", "source_type": "postgres_schema",
            "business_domains": ["database"], "parameters": {},
        })
    if source_type in (None, "pdf"):
        for name in ("pdf_pages", "pdf_paragraphs", "pdf_layout_blocks"):
            strategies.append({
                "name": name, "version": "1", "source_type": "pdf",
                "business_domains": [
                    "requirements", "architecture", "api", "database", "sop", "general"
                ],
                "parameters": {
                    "max_tokens": {"min": 50, "max": 2000},
                    "overlap_tokens": {"min": 0, "max": 500},
                },
            })
    # 通过构造默认注册表确保服务启动时策略注册本身有效。
    assert registry is not None
    return strategies
