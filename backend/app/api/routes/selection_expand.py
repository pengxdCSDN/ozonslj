"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_expand_result_gateway, get_store_workspace_gateway
from backend.app.domain.selection_expand import (
    ExpandInput,
    ExpandResult,
    ExpandResultGateway,
    expand_product,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/selection/expand", tags=["selection"])


class ExpandPayload(BaseModel):
    """说明 ExpandPayload 的职责、状态边界和对外协作关系。"""
    seed_product: str
    core_keywords: list[str] = []
    related_keywords: list[str] = []
    attributes: list[str] = []
    scenes: list[str] = []
    variants: list[str] = []


@router.post("/run", response_model=ExpandResult)
async def run_expand(payload: ExpandPayload) -> ExpandResult:
    """执行 run_expand 的业务流程并返回该流程的结果。"""
    return expand_product(
        ExpandInput(
            seed_product=payload.seed_product,
            core_keywords=tuple(payload.core_keywords),
            related_keywords=tuple(payload.related_keywords),
            attributes=tuple(payload.attributes),
            scenes=tuple(payload.scenes),
            variants=tuple(payload.variants),
        )
    )


@router.post("/store-workspaces/{workspace_id}/run-and-save", response_model=ExpandResult)
async def run_and_save_expand(
    workspace_id: str,
    payload: ExpandPayload,
    gateway: Annotated[ExpandResultGateway, Depends(get_expand_result_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ExpandResult:
    """执行 run_and_save_expand 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    result = expand_product(
        ExpandInput(
            seed_product=payload.seed_product,
            core_keywords=tuple(payload.core_keywords),
            related_keywords=tuple(payload.related_keywords),
            attributes=tuple(payload.attributes),
            scenes=tuple(payload.scenes),
            variants=tuple(payload.variants),
        )
    )
    return await gateway.save_expansion(workspace_id=workspace_id, result=result)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ExpandResult])
async def list_expand_history(
    workspace_id: str,
    gateway: Annotated[ExpandResultGateway, Depends(get_expand_result_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ExpandResult]:
    """执行 list_expand_history 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_expansions(workspace_id=workspace_id, limit=limit)
