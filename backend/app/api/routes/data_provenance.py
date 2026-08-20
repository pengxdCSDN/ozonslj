"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_data_provenance_gateway, get_store_workspace_gateway
from backend.app.domain.data_provenance import (
    DataProvenance,
    DataProvenanceGateway,
    classify_source,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/data-provenance", tags=["data-quality"])


class ProvenancePayload(BaseModel):
    """说明 ProvenancePayload 的职责、状态边界和对外协作关系。"""
    source: str = Field(min_length=1, max_length=50)
    observed_at: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=300)


@router.post("/classify", response_model=DataProvenance)
async def classify(payload: ProvenancePayload) -> DataProvenance:
    """执行 classify 的业务流程并返回该流程的结果。"""
    return classify_source(**payload.model_dump())


@router.post("/store-workspaces/{workspace_id}/classify-and-save", response_model=DataProvenance)
async def classify_and_save(
    workspace_id: str,
    payload: ProvenancePayload,
    gateway: Annotated[DataProvenanceGateway, Depends(get_data_provenance_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> DataProvenance:
    """保存来源标签，供后续分析回溯数据口径和观测时间。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        provenance = classify_source(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "provenance_invalid", "message": str(error)},
        ) from error
    return await gateway.save(workspace_id=workspace_id, provenance=provenance)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[DataProvenance])
async def list_provenance_history(
    workspace_id: str,
    gateway: Annotated[DataProvenanceGateway, Depends(get_data_provenance_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[DataProvenance]:
    """执行 list_provenance_history 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_history(workspace_id=workspace_id, limit=limit)
