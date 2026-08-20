"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_competitor_seed_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.competitor_seed import (
    CompetitorSeed,
    CompetitorSeedError,
    CompetitorSeedGateway,
    validate_competitor_seed_url,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["competitor-seeds"])


class CreateSeedRequest(BaseModel):
    """说明 CreateSeedRequest 的职责、状态边界和对外协作关系。"""
    url: str


class UpdateSeedRequest(BaseModel):
    """说明 UpdateSeedRequest 的职责、状态边界和对外协作关系。"""
    status: str


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
