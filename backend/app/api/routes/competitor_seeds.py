"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import asdict
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_competitor_seed_gateway,
    get_public_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.application.public_sampling_collector import PublicSamplingCollector
from backend.app.config import get_settings
from backend.app.domain.competitor_seed import (
    CompetitorSeed,
    CompetitorSeedError,
    CompetitorSeedGateway,
    validate_competitor_seed_url,
)
from backend.app.domain.public_snapshot import PublicSnapshotGateway
from backend.app.domain.store_workspace import StoreWorkspaceGateway
from backend.app.infrastructure.public_sampling import PublicHttpFetcher

router = APIRouter(prefix="/v1/store-workspaces", tags=["competitor-seeds"])


class CreateSeedRequest(BaseModel):
    """说明 CreateSeedRequest 的职责、状态边界和对外协作关系。"""
    url: str


class UpdateSeedRequest(BaseModel):
    """说明 UpdateSeedRequest 的职责、状态边界和对外协作关系。"""
    status: str


class CollectSeedRequest(BaseModel):
    """单个种子采样的有限重试参数；域名和 URL 均来自服务端种子事实。"""

    max_attempts: int = Field(default=3, ge=1, le=5)


@router.get("/{workspace_id}/competitor-seeds", response_model=list[CompetitorSeed])
async def list_competitor_seeds(
    workspace_id: str,
    gateway: Annotated[CompetitorSeedGateway, Depends(get_competitor_seed_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[CompetitorSeed]:
    """执行 list_competitor_seeds 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_seeds(workspace_id=workspace_id)


@router.post("/{workspace_id}/competitor-seeds", response_model=CompetitorSeed, status_code=201)
async def create_competitor_seed(
    workspace_id: str,
    payload: CreateSeedRequest,
    gateway: Annotated[CompetitorSeedGateway, Depends(get_competitor_seed_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> CompetitorSeed:
    """执行 create_competitor_seed 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        url = validate_competitor_seed_url(payload.url)
    except CompetitorSeedError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "competitor_seed_invalid", "message": str(error)},
        ) from error
    seeds = await gateway.list_seeds(workspace_id=workspace_id)
    if len(seeds) >= 50 and not any(seed.url == url for seed in seeds):
        raise HTTPException(
            status_code=409,
            detail={"code": "competitor_seed_limit", "message": "单工作区最多维护 50 个竞品种子"},
        )
    return await gateway.create_seed(workspace_id=workspace_id, url=url)


@router.patch("/{workspace_id}/competitor-seeds/{seed_id}", response_model=CompetitorSeed)
async def update_competitor_seed(
    workspace_id: str,
    seed_id: str,
    payload: UpdateSeedRequest,
    gateway: Annotated[CompetitorSeedGateway, Depends(get_competitor_seed_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> CompetitorSeed:
    """执行 update_competitor_seed 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    seed_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if payload.status not in {"active", "paused", "blocked"}:
        raise HTTPException(status_code=422, detail={"code": "competitor_seed_status_invalid"})
    seed = await gateway.update_status(seed_id=seed_id, status=payload.status)
    if seed is None or seed.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail={"code": "competitor_seed_not_found"})
    return seed


@router.post("/{workspace_id}/competitor-seeds/{seed_id}/collect")
async def collect_competitor_seed(
    workspace_id: str,
    seed_id: str,
    payload: CollectSeedRequest,
    gateway: Annotated[CompetitorSeedGateway, Depends(get_competitor_seed_gateway)],
    snapshots: Annotated[PublicSnapshotGateway, Depends(get_public_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> dict[str, object]:
    """按已保存的 active 种子执行受控采样并保存可解析快照。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    seed = next(
        (
            item
            for item in await gateway.list_seeds(workspace_id=workspace_id)
            if item.id == seed_id
        ),
        None,
    )
    if seed is None:
        raise HTTPException(status_code=404, detail={"code": "competitor_seed_not_found"})
    if seed.status != "active":
        raise HTTPException(status_code=409, detail={"code": "competitor_seed_not_active"})
    try:
        settings = get_settings()
    except ValueError as error:
        raise HTTPException(status_code=503, detail={"code": "sampling_not_configured"}) from error
    allowed_hosts = frozenset(
        host.strip().lower()
        for host in settings.public_sampling_allowed_hosts.split(",")
        if host.strip()
    )
    if not allowed_hosts:
        raise HTTPException(status_code=503, detail={"code": "sampling_not_configured"})
    async with httpx.AsyncClient(timeout=10.0) as client:
        fetcher = PublicHttpFetcher(
            client, allowed_hosts=allowed_hosts, user_agent=settings.public_sampling_user_agent
        )
        results, saved = await PublicSamplingCollector(
            snapshots, fetcher.fetch_page
        ).collect(
            workspace_id=workspace_id,
            urls=[seed.url],
            global_limit=1,
            max_attempts=payload.max_attempts,
        )
    return {
        "seed_id": seed.id,
        "results": [asdict(result) for result in results],
        "saved_count": len(saved),
    }
