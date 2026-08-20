"""知识型 RAG 治理领域模型与持久化端口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from backend.app.domain.knowledge_chunking import KnowledgeChunk

KnowledgeSourceType = Literal["markdown", "postgres_schema", "pdf"]
KnowledgeSourceStatus = Literal["active", "paused", "withdrawn", "deleted"]
KnowledgeVersionStatus = Literal["draft", "processing", "published", "withdrawn", "deleted"]
IngestionJobType = Literal["ingest", "index", "withdraw", "delete", "rebuild"]
IngestionJobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    """一个可被治理和版本化的知识来源目录项。"""

    id: str
    organization_id: str
    source_type: KnowledgeSourceType
    business_domain: str
    title: str
    authority_level: Literal["a", "b", "c"]
    sensitivity: Literal["public", "internal", "restricted"]
    status: KnowledgeSourceStatus
    source_locator: str


@dataclass(frozen=True, slots=True)
class KnowledgeVersion:
    """来源的不可变版本；发布状态由数据库唯一索引约束。"""

    id: str
    organization_id: str
    source_id: str
    version_number: int
    content_hash: str
    parser_name: str
    parser_version: str
    cleaner_version: str
    status: KnowledgeVersionStatus


@dataclass(frozen=True, slots=True)
class IngestionJob:
    """摄取/索引任务的持久化状态摘要；Redis 只作为触发信号。"""

    id: str
    organization_id: str
    source_id: str
    document_version_id: str | None
    job_type: IngestionJobType
    status: IngestionJobStatus
    idempotency_key: str
    attempt_count: int
    error_code: str | None
    error_summary: str | None


class KnowledgeGovernanceGateway(Protocol):
    """知识治理用例依赖的持久化端口。"""

    async def create_source(self, source: KnowledgeSource) -> KnowledgeSource:
        """执行 create_source 的业务流程并返回该流程的结果。"""

    async def create_version(self, version: KnowledgeVersion) -> KnowledgeVersion:
        """执行 create_version 的业务流程并返回该流程的结果。"""

    async def create_job(self, job: IngestionJob) -> IngestionJob:
        """执行 create_job 的业务流程并返回该流程的结果。"""

    async def set_version_status(
        self, *, organization_id: str, version_id: str, status: KnowledgeVersionStatus
    ) -> KnowledgeVersion:
        """执行 set_version_status 的业务流程并返回该流程的结果。"""

    async def set_source_status(
        self, *, organization_id: str, source_id: str, status: KnowledgeSourceStatus
    ) -> KnowledgeSource:
        """执行 set_source_status 的业务流程并返回该流程的结果。"""


class KnowledgeChunkGateway(Protocol):
    """切片目录生命周期端口；向量索引由 Worker 通过同一切片 ID 对账。"""

    async def upsert_chunks(
        self, *, organization_id: str, chunks: list[KnowledgeChunk]
    ) -> None:
        """执行 upsert_chunks 的业务流程并返回该流程的结果。"""

    async def set_chunk_status(
        self, *, organization_id: str, chunk_ids: list[str], status: str
    ) -> None:
        """执行 set_chunk_status 的业务流程并返回该流程的结果。"""
