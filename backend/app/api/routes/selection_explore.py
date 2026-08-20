"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_explore_opportunity_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.selection_explore import (
    ExploreFilters,
    ExploreInput,
    ExploreOpportunity,
    ExploreOpportunityGateway,
    explore_opportunities,
    filter_opportunities,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/selection/explore", tags=["selection"])


class ExploreItemPayload(BaseModel):
    """说明 ExploreItemPayload 的职责、状态边界和对外协作关系。"""
    keyword: str
    search_count: int = Field(ge=0)
    conversion_rate: float | None = Field(default=None, ge=0)
    sample_count: int = Field(default=0, ge=0)
    median_price_minor: int | None = Field(default=None, ge=0)
    own_stock: int = Field(default=0, ge=0)
    own_sales: int = Field(default=0, ge=0)


class ExplorePayload(BaseModel):
    """说明 ExplorePayload 的职责、状态边界和对外协作关系。"""
    items: list[ExploreItemPayload]
    min_score: float = Field(default=0, ge=0, le=100)
    min_search_count: int = Field(default=0, ge=0)
    min_conversion_rate: float | None = Field(default=None, ge=0)
    coverage_gap_only: bool = False


def _run(payload: ExplorePayload) -> list[ExploreOpportunity]:
    """执行内部步骤 _run，供同一模块的公开流程复用。"""
    scored = explore_opportunities([ExploreInput(**item.model_dump()) for item in payload.items])
    return filter_opportunities(
        scored,
        ExploreFilters(
            min_score=payload.min_score,
            min_search_count=payload.min_search_count,
            min_conversion_rate=payload.min_conversion_rate,
            coverage_gap_only=payload.coverage_gap_only,
        ),
    )


@router.post("/run", response_model=list[ExploreOpportunity])
async def run_explore(payload: ExplorePayload) -> list[ExploreOpportunity]:
    """执行 run_explore 的业务流程并返回该流程的结果。"""
    return _run(payload)


@router.post(
    "/store-workspaces/{workspace_id}/run-and-save",
    response_model=list[ExploreOpportunity],
)
async def run_and_save_explore(
    workspace_id: str,
    payload: ExplorePayload,
    gateway: Annotated[ExploreOpportunityGateway, Depends(get_explore_opportunity_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[ExploreOpportunity]:
    """执行 run_and_save_explore 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    opportunities = _run(payload)
    return await gateway.save_opportunities(workspace_id=workspace_id, opportunities=opportunities)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ExploreOpportunity])
async def list_explore_history(
    workspace_id: str,
    gateway: Annotated[ExploreOpportunityGateway, Depends(get_explore_opportunity_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ExploreOpportunity]:
    """执行 list_explore_history 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_opportunities(workspace_id=workspace_id, limit=limit)
