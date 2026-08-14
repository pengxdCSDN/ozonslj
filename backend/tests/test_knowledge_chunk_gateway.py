"""切片目录适配器 SQL 契约测试。"""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.infrastructure.postgres.knowledge_chunks import PostgresKnowledgeChunkGateway


class FakeConnection:
    def __init__(self) -> None:
        self.execute = AsyncMock()

    async def __aenter__(self) -> "FakeConnection":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None

    def transaction(self) -> "FakeConnection":
        return self


class FakePool:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    def connection(self) -> FakeConnection:
        return self._connection


def _chunk() -> KnowledgeChunk:
    metadata = ChunkMetadata(
        document_id="d", document_version_id="v", business_domain="general",
        source_type="markdown", source_level="b", language="zh-CN", title_path=("说明",),
        source_locator="docs/a.md", chunk_strategy="markdown_sections", chunk_strategy_version="1",
        status="draft",
    )
    return KnowledgeChunk("c1", "正文", "h1", 0, metadata)


@pytest.mark.asyncio
async def test_upsert_and_status_update_are_parameterized() -> None:
    connection = FakeConnection()
    gateway = PostgresKnowledgeChunkGateway(FakePool(connection))  # type: ignore[arg-type]
    await gateway.upsert_chunks(organization_id="org-1", chunks=[_chunk()])
    await gateway.set_chunk_status(organization_id="org-1", chunk_ids=["c1"], status="withdrawn")
    assert connection.execute.await_count == 2
    assert "ANY(%s)" in connection.execute.await_args_list[1].args[0]
