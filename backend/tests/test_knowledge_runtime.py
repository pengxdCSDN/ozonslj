"""运行时索引的发布、撤回与删除回归测试。"""

import pytest

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_runtime import KnowledgeRuntimeIndex


def _chunk(version_id: str, text: str) -> KnowledgeChunk:
    metadata = ChunkMetadata(
        document_id="doc", document_version_id=version_id, business_domain="general",
        source_type="markdown", source_level="c", language="zh-CN", title_path=("测试",),
        source_locator="test.md", chunk_strategy="markdown_section",
        chunk_strategy_version="1", status="draft",
    )
    return KnowledgeChunk(
        chunk_id=f"chunk-{version_id}", content=text, content_hash=f"hash-{version_id}",
        ordinal=0, metadata=metadata,
    )


@pytest.mark.asyncio
async def test_runtime_publishes_and_withdraws_both_retrieval_channels() -> None:
    runtime = KnowledgeRuntimeIndex()
    runtime.stage("v1", (_chunk("v1", "库存安全线是 10 件"),))
    await runtime.publish("v1")
    answered = await runtime.engine().answer("如何查看库存安全线")
    assert answered[0].status == "answered"
    assert answered[0].citations[0].chunk_id == "chunk-v1"

    await runtime.withdraw("v1")
    withdrawn = await runtime.engine().answer("如何查看库存安全线")
    assert withdrawn[0].status in {"unknown", "unsupported", "needs_clarification"}
