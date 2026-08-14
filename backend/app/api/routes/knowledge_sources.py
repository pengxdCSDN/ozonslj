"""知识源与版本生命周期 API。"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.knowledge_governance import KnowledgeSource, KnowledgeVersion
from backend.app.domain.knowledge_runtime import get_knowledge_runtime

router = APIRouter(prefix="/v1/knowledge-sources", tags=["knowledge-governance"])


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
    return KnowledgeSourceResponse(
        id=source.id,
        title=source.title,
        source_type=source.source_type,
        business_domain=source.business_domain,
        source_locator=source.source_locator,
        authority_level=source.authority_level,
        sensitivity=source.sensitivity,
        status=source.status,
    )


def _version_response(version: KnowledgeVersion) -> KnowledgeVersionResponse:
    return KnowledgeVersionResponse(
        id=version.id,
        source_id=version.source_id,
        version_number=version.version_number,
        content_hash=version.content_hash,
        status=version.status,
    )


@router.post("", response_model=KnowledgeSourceResponse, status_code=201)
async def create_knowledge_source(payload: KnowledgeSourceCreate) -> KnowledgeSourceResponse:
    runtime = get_knowledge_runtime()
    source = KnowledgeSource(
        id=str(uuid4()),
        organization_id=runtime.organization_id,
        source_type=payload.source_type,  # type: ignore[arg-type]
        business_domain=payload.business_domain,
        title=payload.title,
        authority_level=payload.authority_level,  # type: ignore[arg-type]
        sensitivity=payload.sensitivity,  # type: ignore[arg-type]
        status="active",
        source_locator=payload.source_locator,
    )
    try:
        return _response(await runtime.create_source(source))
    except Exception as error:
        # 不把数据库连接串、SQL 或上游响应写入 API；唯一约束冲突也只返回业务错误。
        raise HTTPException(status_code=409, detail="知识源无法创建，可能已存在相同来源") from error


@router.get("", response_model=list[KnowledgeSourceResponse])
async def list_knowledge_sources() -> list[KnowledgeSourceResponse]:
    runtime = get_knowledge_runtime()
    return [_response(source) for source in await runtime.list_sources()]


@router.post("/{source_id}/withdraw", response_model=KnowledgeSourceResponse)
async def withdraw_knowledge_source(source_id: str) -> KnowledgeSourceResponse:
    runtime = get_knowledge_runtime()
    source = await runtime.source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    for version in await runtime.list_versions(source_id):
        if await runtime.has_published_version(version.id):
            await runtime.withdraw(version.id)
    return _response(await runtime.set_source_status(source_id, "withdrawn"))


@router.post("/{source_id}/pause", response_model=KnowledgeSourceResponse)
async def pause_knowledge_source(source_id: str) -> KnowledgeSourceResponse:
    runtime = get_knowledge_runtime()
    source = await runtime.source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    if source.status != "active":
        raise HTTPException(status_code=409, detail="只有 active 知识源可以暂停")
    return _response(await runtime.set_source_status(source_id, "paused"))


@router.post("/{source_id}/resume", response_model=KnowledgeSourceResponse)
async def resume_knowledge_source(source_id: str) -> KnowledgeSourceResponse:
    runtime = get_knowledge_runtime()
    source = await runtime.source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    if source.status != "paused":
        raise HTTPException(status_code=409, detail="只有 paused 知识源可以恢复")
    return _response(await runtime.set_source_status(source_id, "active"))


@router.delete("/{source_id}", response_model=KnowledgeSourceResponse)
async def delete_knowledge_source(source_id: str) -> KnowledgeSourceResponse:
    runtime = get_knowledge_runtime()
    source = await runtime.source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    for version in await runtime.list_versions(source_id):
        await runtime.delete(version.id)
    return _response(await runtime.set_source_status(source_id, "deleted"))


@router.post("/{source_id}/versions", response_model=KnowledgeVersionResponse, status_code=201)
async def create_knowledge_version(
    source_id: str, payload: KnowledgeVersionCreate
) -> KnowledgeVersionResponse:
    runtime = get_knowledge_runtime()
    source = await runtime.source(source_id)
    if source is None or source.status in {"withdrawn", "deleted"}:
        raise HTTPException(status_code=404, detail="知识源不存在或不可新增版本")
    version = KnowledgeVersion(
        id=str(uuid4()),
        organization_id=source.organization_id,
        source_id=source_id,
        version_number=await runtime.next_version_number(source_id),
        content_hash=payload.content_hash,
        parser_name=payload.parser_name,
        parser_version=payload.parser_version,
        cleaner_version=payload.cleaner_version,
        status="draft",
    )
    try:
        return _version_response(await runtime.create_version(version))
    except Exception as error:
        raise HTTPException(status_code=409, detail="知识版本无法创建") from error


@router.get("/{source_id}/versions", response_model=list[KnowledgeVersionResponse])
async def list_knowledge_versions(source_id: str) -> list[KnowledgeVersionResponse]:
    runtime = get_knowledge_runtime()
    if await runtime.source(source_id) is None:
        raise HTTPException(status_code=404, detail="知识源不存在")
    return [_version_response(version) for version in await runtime.list_versions(source_id)]


@router.post("/versions/{version_id}/publish", response_model=KnowledgeVersionResponse)
async def publish_knowledge_version(version_id: str) -> KnowledgeVersionResponse:
    runtime = get_knowledge_runtime()
    version = await runtime.version(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="知识版本不存在")
    if version.status != "draft":
        raise HTTPException(status_code=409, detail="只有 draft 版本可以发布")
    if await runtime.has_staged(version_id):
        await runtime.publish(version_id)
    else:
        # 允许先建立目录再发布的本地治理测试；生产环境会拒绝无切片发布。
        if runtime.persistent:
            raise HTTPException(status_code=409, detail="版本尚未完成切片，不能发布")
        for other in await runtime.list_versions(version.source_id):
            if other.id != version_id and other.status == "published":
                await runtime.set_version_status(other.id, "withdrawn")
        await runtime.set_version_status(version_id, "published")
    published = await runtime.version(version_id)
    assert published is not None
    return _version_response(published)


@router.post("/versions/{version_id}/withdraw", response_model=KnowledgeVersionResponse)
async def withdraw_knowledge_version(version_id: str) -> KnowledgeVersionResponse:
    runtime = get_knowledge_runtime()
    version = await runtime.version(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="知识版本不存在")
    if version.status not in {"published", "draft"}:
        raise HTTPException(status_code=409, detail="当前版本状态不允许撤回")
    if version.status == "published":
        await runtime.withdraw(version_id)
    else:
        await runtime.set_version_status(version_id, "withdrawn")
    withdrawn = await runtime.version(version_id)
    assert withdrawn is not None
    return _version_response(withdrawn)
