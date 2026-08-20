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

    async def create_source(self, source: KnowledgeSource) -> KnowledgeSource:
        """执行 create_source 的业务流程并返回该流程的结果。

Args:
    source: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_sources(self) -> list[KnowledgeSource]:
        """执行 list_sources 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""

    async def source(self, source_id: str) -> KnowledgeSource | None:
        """执行 source 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def set_source_status(self, source_id: str, status: str) -> KnowledgeSource:
        """执行 set_source_status 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        """执行 create_version 的业务流程并返回该流程的结果。

Args:
    version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def next_version_number(self, source_id: str) -> int:
        """执行 next_version_number 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_versions(self, source_id: str) -> list[KnowledgeVersion]:
        """执行 list_versions 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def version(self, version_id: str) -> KnowledgeVersion | None:
        """执行 version 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def set_version_status(self, version_id: str, status: str) -> KnowledgeVersion:
        """执行 set_version_status 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    def stage(
        self, version_id: str, chunks: tuple[KnowledgeChunk, ...]
    ) -> Awaitable[None] | None:
        """执行 stage 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。
    chunks: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def has_staged(self, version_id: str) -> bool:
        """执行 has_staged 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def has_published_version(self, version_id: str) -> bool:
        """执行 has_published_version 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def has_published(self) -> bool:
        """执行 has_published 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""

    async def publish(self, version_id: str) -> int:
        """执行 publish 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def withdraw(self, version_id: str) -> int:
        """执行 withdraw 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def delete(self, version_id: str) -> int:
        """执行 delete 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def rebuild(self) -> int:
        """执行 rebuild 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""

    def engine(self) -> KnowledgeQueryEngine | Awaitable[KnowledgeQueryEngine]:
        """执行 engine 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""

    async def translate(self, texts: list[str]) -> list[str]:
        """执行 translate 的业务流程并返回该流程的结果。

Args:
    texts: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def close(self) -> None:
        """执行 close 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""


class KnowledgeRuntimeIndex:
    """本地测试用内存运行时；生产服务不会使用该实现。"""

    organization_id = "local"
    persistent = False

    def __init__(self) -> None:
        """初始化对象依赖和运行时状态。
Returns:
    返回调用完成后的领域结果。"""
        self._embedding = DeterministicEmbedding()
        self._keyword = InMemoryKeywordIndex()
        self._vector = InMemoryVectorIndex(dimension=self._embedding.dimension)
        self._sources: dict[str, KnowledgeSource] = {}
        self._versions: dict[str, KnowledgeVersion] = {}
        self._staged: dict[str, tuple[KnowledgeChunk, ...]] = {}
        self._published: dict[str, tuple[KnowledgeChunk, ...]] = {}
        self._indexed_chunk_ids: set[str] = set()

    async def create_source(self, source: KnowledgeSource) -> KnowledgeSource:
        """执行 create_source 的业务流程并返回该流程的结果。

Args:
    source: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        stored = replace(source, organization_id=self.organization_id)
        self._sources[stored.id] = stored
        return stored

    async def list_sources(self) -> list[KnowledgeSource]:
        """执行 list_sources 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        return list(self._sources.values())

    async def source(self, source_id: str) -> KnowledgeSource | None:
        """执行 source 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return self._sources.get(source_id)

    async def set_source_status(self, source_id: str, status: str) -> KnowledgeSource:
        """执行 set_source_status 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    KeyError: 业务约束或外部依赖失败时抛出。
"""
        source = self._sources.get(source_id)
        if source is None:
            raise KeyError(source_id)
        updated = replace(source, status=status)  # type: ignore[arg-type]
        self._sources[source_id] = updated
        return updated

    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        """执行 create_version 的业务流程并返回该流程的结果。

Args:
    version: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        stored = replace(version, organization_id=self.organization_id)
        self._versions[stored.id] = stored
        return stored

    async def next_version_number(self, source_id: str) -> int:
        """执行 next_version_number 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        numbers = [
            version.version_number
            for version in self._versions.values()
            if version.source_id == source_id
        ]
        return max(numbers, default=0) + 1

    async def list_versions(self, source_id: str) -> list[KnowledgeVersion]:
        """执行 list_versions 的业务流程并返回该流程的结果。

Args:
    source_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return [version for version in self._versions.values() if version.source_id == source_id]

    async def version(self, version_id: str) -> KnowledgeVersion | None:
        """执行 version 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return self._versions.get(version_id)

    async def set_version_status(self, version_id: str, status: str) -> KnowledgeVersion:
        """执行 set_version_status 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    KeyError: 业务约束或外部依赖失败时抛出。
"""
        version = self._versions.get(version_id)
        if version is None:
            raise KeyError(version_id)
        updated = replace(version, status=status)  # type: ignore[arg-type]
        self._versions[version_id] = updated
        return updated

    def stage(self, version_id: str, chunks: tuple[KnowledgeChunk, ...]) -> None:
        """质量门禁通过后写入草稿区；未发布版本不会进入检索索引。

Args:
    version_id: 参数语义、输入边界和安全约束。
    chunks: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._staged[version_id] = chunks

    async def has_staged(self, version_id: str) -> bool:
        """执行 has_staged 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return version_id in self._staged

    async def has_published_version(self, version_id: str) -> bool:
        """执行 has_published_version 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return version_id in self._published

    async def has_published(self) -> bool:
        """执行 has_published 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        return bool(self._published)

    async def publish(self, version_id: str) -> int:
        """执行 publish 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    KeyError: 业务约束或外部依赖失败时抛出。
"""
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
        """执行 withdraw 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        version = self._versions.get(version_id)
        if version is not None:
            self._versions[version_id] = replace(version, status="withdrawn")
        removed = len(self._published.pop(version_id, ()))
        await self._rebuild()
        return removed

    async def delete(self, version_id: str) -> int:
        """执行 delete 的业务流程并返回该流程的结果。

Args:
    version_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        version = self._versions.get(version_id)
        if version is not None:
            self._versions[version_id] = replace(version, status="deleted")
        removed = len(self._published.pop(version_id, ()))
        removed += len(self._staged.pop(version_id, ()))
        await self._rebuild()
        return removed

    async def rebuild(self) -> int:
        """从 PostgreSQL/内存事实重新生成当前发布索引，供故障恢复任务使用。
Returns:
    返回调用完成后的领域结果。"""
        await self._rebuild()
        return len(self._indexed_chunk_ids)

    def engine(self) -> KnowledgeQueryEngine:
        """执行 engine 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
        return KnowledgeQueryEngine(
            embedding=self._embedding,
            keyword_index=self._keyword,
            vector_index=self._vector,
        )

    async def translate(self, texts: list[str]) -> list[str]:
        """离线环境不调用外部模型，仅返回原文，避免测试误触真实供应商。

Args:
    texts: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return list(texts)

    async def close(self) -> None:
        """内存实现无资源需要释放；保持与生产运行时同一生命周期接口。
Returns:
    返回调用完成后的领域结果。"""
        return None

    async def _rebuild(self) -> None:
        """执行内部步骤 _rebuild，供同一模块的公开流程复用。
Returns:
    返回调用完成后的领域结果。"""
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
    """按部署环境选择运行时；生产环境缺少配置时快速失败而不伪造回答。
Returns:
    返回调用完成后的领域结果。"""

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
    """兼容本地同步测试实现与生产异步数据库实现。

Args:
    runtime: 参数语义、输入边界和安全约束。
    version_id: 参数语义、输入边界和安全约束。
    chunks: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    result = runtime.stage(version_id, chunks)
    if inspect.isawaitable(result):
        await result


async def resolve_knowledge_engine(runtime: KnowledgeRuntimePort) -> KnowledgeQueryEngine:
    """兼容同步内存索引和异步生产索引的查询入口。

Args:
    runtime: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    result = runtime.engine()
    return await result if inspect.isawaitable(result) else result


async def close_knowledge_runtime() -> None:
    """应用退出时关闭生产 RAG 连接池。
Returns:
    返回调用完成后的领域结果。"""
    if _production_runtime is not None:
        await _production_runtime.close()
