"""知识源生命周期 API：先提供可运行的内存实现，持久化由治理网关承接。"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.knowledge_governance import KnowledgeSource, KnowledgeVersion
from backend.app.domain.knowledge_runtime import runtime_index

router = APIRouter(prefix="/v1/knowledge-sources", tags=["knowledge-governance"])
_sources: dict[str, KnowledgeSource] = {}
_versions: dict[str, KnowledgeVersion] = {}


class KnowledgeSourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_type: str = Field(pattern="^(markdown|postgres_schema|pdf)$")
    business_domain: str = Field(min_length=1, max_length=80)
    source_locator: str = Field(min_length=1, max_length=500)
    authority_level: str = Field(default="b", pattern="^(a|b|c)$")
    sensitivity: str = Field(default="internal", pattern="^(public|internal|restricted)$")


class KnowledgeSourceResponse(BaseModel):
    id: str
    title: str
    source_type: str
    business_domain: str
    source_locator: str
    authority_level: str
    sensitivity: str
    status: str


class KnowledgeVersionCreate(BaseModel):
    content_hash: str = Field(min_length=1, max_length=128)
    parser_name: str = Field(min_length=1, max_length=100)
    parser_version: str = Field(min_length=1, max_length=40)
    cleaner_version: str = Field(min_length=1, max_length=40)


class KnowledgeVersionResponse(BaseModel):
    id: str
    source_id: str
    version_number: int
    content_hash: str
    status: str


def _response(source: KnowledgeSource) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(**{
        "id": source.id, "title": source.title, "source_type": source.source_type,
        "business_domain": source.business_domain, "source_locator": source.source_locator,
        "authority_level": source.authority_level, "sensitivity": source.sensitivity,
        "status": source.status,
    })


def _version_response(version: KnowledgeVersion) -> KnowledgeVersionResponse:
    return KnowledgeVersionResponse(
        id=version.id, source_id=version.source_id, version_number=version.version_number,
        content_hash=version.content_hash, status=version.status,
    )


@router.post("", response_model=KnowledgeSourceResponse, status_code=201)
async def create_knowledge_source(payload: KnowledgeSourceCreate) -> KnowledgeSourceResponse:
    source = KnowledgeSource(
        id=str(uuid4()), organization_id="local", source_type=payload.source_type,  # type: ignore[arg-type]
        business_domain=payload.business_domain, title=payload.title,
        authority_level=payload.authority_level, sensitivity=payload.sensitivity,  # type: ignore[arg-type]
        status="active", source_locator=payload.source_locator,
    )
    _sources[source.id] = source
    return _response(source)


@router.get("", response_model=list[KnowledgeSourceResponse])
async def list_knowledge_sources() -> list[KnowledgeSourceResponse]:
    return [_response(source) for source in _sources.values()]


@router.post("/{source_id}/withdraw", response_model=KnowledgeSourceResponse)
async def withdraw_knowledge_source(source_id: str) -> KnowledgeSourceResponse:
    source = _sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    for version in _versions.values():
        if version.source_id == source_id and runtime_index.has_published_version(version.id):
            await runtime_index.withdraw(version.id)
    withdrawn = replace(source, status="withdrawn")
    _sources[source_id] = withdrawn
    return _response(withdrawn)


@router.post("/{source_id}/pause", response_model=KnowledgeSourceResponse)
async def pause_knowledge_source(source_id: str) -> KnowledgeSourceResponse:
    source = _sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    if source.status != "active":
        raise HTTPException(status_code=409, detail="只有 active 知识源可以暂停")
    paused = replace(source, status="paused")
    _sources[source_id] = paused
    return _response(paused)


@router.post("/{source_id}/resume", response_model=KnowledgeSourceResponse)
async def resume_knowledge_source(source_id: str) -> KnowledgeSourceResponse:
    source = _sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    if source.status != "paused":
        raise HTTPException(status_code=409, detail="只有 paused 知识源可以恢复")
    resumed = replace(source, status="active")
    _sources[source_id] = resumed
    return _response(resumed)


@router.delete("/{source_id}", response_model=KnowledgeSourceResponse)
async def delete_knowledge_source(source_id: str) -> KnowledgeSourceResponse:
    source = _sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    for version in _versions.values():
        if version.source_id == source_id:
            await runtime_index.delete(version.id)
    deleted = replace(source, status="deleted")
    _sources[source_id] = deleted
    return _response(deleted)


@router.post("/{source_id}/versions", response_model=KnowledgeVersionResponse, status_code=201)
async def create_knowledge_version(
    source_id: str, payload: KnowledgeVersionCreate
) -> KnowledgeVersionResponse:
    source = _sources.get(source_id)
    if source is None or source.status in {"withdrawn", "deleted"}:
        raise HTTPException(status_code=404, detail="知识源不存在或不可新增版本")
    existing = [
        version.version_number
        for version in _versions.values()
        if version.source_id == source_id
    ]
    version = KnowledgeVersion(
        id=str(uuid4()), organization_id=source.organization_id, source_id=source_id,
        version_number=max(existing, default=0) + 1, content_hash=payload.content_hash,
        parser_name=payload.parser_name, parser_version=payload.parser_version,
        cleaner_version=payload.cleaner_version, status="draft",
    )
    _versions[version.id] = version
    return _version_response(version)


@router.get("/{source_id}/versions", response_model=list[KnowledgeVersionResponse])
async def list_knowledge_versions(source_id: str) -> list[KnowledgeVersionResponse]:
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail="知识源不存在")
    return [
        _version_response(version)
        for version in _versions.values()
        if version.source_id == source_id
    ]


@router.post("/versions/{version_id}/publish", response_model=KnowledgeVersionResponse)
async def publish_knowledge_version(version_id: str) -> KnowledgeVersionResponse:
    version = _versions.get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="知识版本不存在")
    if version.status != "draft":
        raise HTTPException(status_code=409, detail="只有 draft 版本可以发布")
    # 兼容仅维护目录的 Stub：只有实际摄取过的版本才触发运行时索引发布。
    if runtime_index.has_staged(version_id):
        await runtime_index.publish(version_id)
    for other_id, other in list(_versions.items()):
        if other.source_id == version.source_id and other.status == "published":
            if runtime_index.has_published_version(other_id):
                await runtime_index.withdraw(other_id)
            _versions[other_id] = replace(other, status="withdrawn")
    published = replace(version, status="published")
    _versions[version_id] = published
    return _version_response(published)


@router.post("/versions/{version_id}/withdraw", response_model=KnowledgeVersionResponse)
async def withdraw_knowledge_version(version_id: str) -> KnowledgeVersionResponse:
    version = _versions.get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="知识版本不存在")
    if version.status not in {"published", "draft"}:
        raise HTTPException(status_code=409, detail="当前版本状态不允许撤回")
    if version.status == "published":
        await runtime_index.withdraw(version_id)
    withdrawn = replace(version, status="withdrawn")
    _versions[version_id] = withdrawn
    return _version_response(withdrawn)
