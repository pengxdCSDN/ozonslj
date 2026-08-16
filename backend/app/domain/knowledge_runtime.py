"""知识 RAG 运行时端口与本地测试实现。

生产环境的事实存储和向量索引由 PostgreSQL + Chroma 承载；本模块只保留
不依赖外部服务的内存实现，供单元测试和本地离线开发使用。路由通过
``get_knowledge_runtime`` 获取实现，避免把存储选择散落在 API 层。
"""

from __future__ import annotations

import inspect
import os
from collections.abc import Awaitable
from dataclasses import replace
from typing import Protocol

from backend.app.domain.knowledge_chunking import KnowledgeChunk
from backend.app.domain.knowledge_governance import KnowledgeSource, KnowledgeVersion
from backend.app.domain.knowledge_query import KnowledgeQueryEngine
from backend.app.domain.knowledge_retrieval import (
    DeterministicEmbedding,
    InMemoryKeywordIndex,
    InMemoryVectorIndex,
)


class KnowledgeRuntimePort(Protocol):
    """知识来源、版本、切片和检索索引的统一异步端口。"""

    organization_id: str
    persistent: bool

    async def create_source(self, source: KnowledgeSource) -> KnowledgeSource: ...

    async def list_sources(self) -> list[KnowledgeSource]: ...

    async def source(self, source_id: str) -> KnowledgeSource | None: ...

    async def set_source_status(self, source_id: str, status: str) -> KnowledgeSource: ...

    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion: ...

    async def next_version_number(self, source_id: str) -> int: ...

    async def list_versions(self, source_id: str) -> list[KnowledgeVersion]: ...

    async def version(self, version_id: str) -> KnowledgeVersion | None: ...

    async def set_version_status(self, version_id: str, status: str) -> KnowledgeVersion: ...

    def stage(
        self, version_id: str, chunks: tuple[KnowledgeChunk, ...]
    ) -> Awaitable[None] | None: ...

    async def has_staged(self, version_id: str) -> bool: ...

    async def has_published_version(self, version_id: str) -> bool: ...

    async def has_published(self) -> bool: ...

    async def publish(self, version_id: str) -> int: ...

    async def withdraw(self, version_id: str) -> int: ...

    async def delete(self, version_id: str) -> int: ...

    async def rebuild(self) -> int: ...

    def engine(self) -> KnowledgeQueryEngine | Awaitable[KnowledgeQueryEngine]: ...

    async def close(self) -> None: ...


class KnowledgeRuntimeIndex:
    """本地测试用内存运行时；生产服务不会使用该实现。"""

    organization_id = "local"
    persistent = False

    def __init__(self) -> None:
        self._embedding = DeterministicEmbedding()
        self._keyword = InMemoryKeywordIndex()
        self._vector = InMemoryVectorIndex(dimension=self._embedding.dimension)
        self._sources: dict[str, KnowledgeSource] = {}
        self._versions: dict[str, KnowledgeVersion] = {}
        self._staged: dict[str, tuple[KnowledgeChunk, ...]] = {}
        self._published: dict[str, tuple[KnowledgeChunk, ...]] = {}
        self._indexed_chunk_ids: set[str] = set()

    async def create_source(self, source: KnowledgeSource) -> KnowledgeSource:
        stored = replace(source, organization_id=self.organization_id)
        self._sources[stored.id] = stored
        return stored

    async def list_sources(self) -> list[KnowledgeSource]:
        return list(self._sources.values())

    async def source(self, source_id: str) -> KnowledgeSource | None:
        return self._sources.get(source_id)

    async def set_source_status(self, source_id: str, status: str) -> KnowledgeSource:
        source = self._sources.get(source_id)
        if source is None:
            raise KeyError(source_id)
        updated = replace(source, status=status)  # type: ignore[arg-type]
        self._sources[source_id] = updated
        return updated

    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        stored = replace(version, organization_id=self.organization_id)
        self._versions[stored.id] = stored
        return stored

    async def next_version_number(self, source_id: str) -> int:
        numbers = [
            version.version_number
            for version in self._versions.values()
            if version.source_id == source_id
        ]
        return max(numbers, default=0) + 1

    async def list_versions(self, source_id: str) -> list[KnowledgeVersion]:
        return [version for version in self._versions.values() if version.source_id == source_id]

    async def version(self, version_id: str) -> KnowledgeVersion | None:
        return self._versions.get(version_id)

    async def set_version_status(self, version_id: str, status: str) -> KnowledgeVersion:
        version = self._versions.get(version_id)
        if version is None:
            raise KeyError(version_id)
        updated = replace(version, status=status)  # type: ignore[arg-type]
        self._versions[version_id] = updated
        return updated

    def stage(self, version_id: str, chunks: tuple[KnowledgeChunk, ...]) -> None:
        """质量门禁通过后写入草稿区；未发布版本不会进入检索索引。"""
        self._staged[version_id] = chunks

    async def has_staged(self, version_id: str) -> bool:
        return version_id in self._staged

    async def has_published_version(self, version_id: str) -> bool:
        return version_id in self._published

    async def has_published(self) -> bool:
        return bool(self._published)

    async def publish(self, version_id: str) -> int:
        chunks = self._staged.get(version_id)
        version = self._versions.get(version_id)
        if chunks is None:
            raise KeyError(version_id)
        if version is not None:
            for other_id, other in list(self._versions.items()):
                if other.source_id == version.source_id and other.status == "published":
                    self._versions[other_id] = replace(other, status="withdrawn")
                    self._published.pop(other_id, None)
        published = tuple(
            replace(chunk, metadata=replace(chunk.metadata, status="published"))
            for chunk in chunks
        )
        self._published[version_id] = published
        if version is not None:
            self._versions[version_id] = replace(version, status="published")
        await self._rebuild()
        return len(published)

    async def withdraw(self, version_id: str) -> int:
        version = self._versions.get(version_id)
        if version is not None:
            self._versions[version_id] = replace(version, status="withdrawn")
        removed = len(self._published.pop(version_id, ()))
        await self._rebuild()
        return removed

    async def delete(self, version_id: str) -> int:
        version = self._versions.get(version_id)
        if version is not None:
            self._versions[version_id] = replace(version, status="deleted")
        removed = len(self._published.pop(version_id, ()))
        removed += len(self._staged.pop(version_id, ()))
        await self._rebuild()
        return removed

    async def rebuild(self) -> int:
        """从 PostgreSQL/内存事实重新生成当前发布索引，供故障恢复任务使用。"""
        await self._rebuild()
        return len(self._indexed_chunk_ids)

    def engine(self) -> KnowledgeQueryEngine:
        return KnowledgeQueryEngine(
            embedding=self._embedding,
            keyword_index=self._keyword,
            vector_index=self._vector,
        )

    async def close(self) -> None:
        """内存实现无资源需要释放；保持与生产运行时同一生命周期接口。"""
        return None

    async def _rebuild(self) -> None:
        chunks = [chunk for group in self._published.values() for chunk in group]
        await self._keyword.replace(chunks)
        await self._vector.delete(list(self._indexed_chunk_ids))
        if chunks:
            await self._vector.upsert(
                chunks, await self._embedding.embed([chunk.content for chunk in chunks])
            )
        self._indexed_chunk_ids = {chunk.chunk_id for chunk in chunks}


runtime_index = KnowledgeRuntimeIndex()
_production_runtime: KnowledgeRuntimePort | None = None


def get_knowledge_runtime() -> KnowledgeRuntimePort:
    """按部署环境选择运行时；生产环境缺少配置时快速失败而不伪造回答。"""

    global _production_runtime
    app_env = os.getenv("APP_ENV", "local").lower()
    # 配置了 CHROMA_URL 的本地集成环境也使用真实持久化运行时；只有未配置
    # 外部依赖的纯单元测试才回落到内存实现。
    if app_env != "production" and not os.getenv("CHROMA_URL"):
        return runtime_index
    if _production_runtime is None:
        from backend.app.config import get_settings
        from backend.app.infrastructure.postgres.knowledge_runtime import (
            PostgresChromaKnowledgeRuntime,
        )

        _production_runtime = PostgresChromaKnowledgeRuntime(get_settings())
    return _production_runtime


async def stage_knowledge_chunks(
    runtime: KnowledgeRuntimePort, version_id: str, chunks: tuple[KnowledgeChunk, ...]
) -> None:
    """兼容本地同步测试实现与生产异步数据库实现。"""
    result = runtime.stage(version_id, chunks)
    if inspect.isawaitable(result):
        await result


async def resolve_knowledge_engine(runtime: KnowledgeRuntimePort) -> KnowledgeQueryEngine:
    """兼容同步内存索引和异步生产索引的查询入口。"""
    result = runtime.engine()
    return await result if inspect.isawaitable(result) else result


async def close_knowledge_runtime() -> None:
    """应用退出时关闭生产 RAG 连接池。"""
    if _production_runtime is not None:
        await _production_runtime.close()
