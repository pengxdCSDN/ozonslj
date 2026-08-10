from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_execution_result_gateway, get_store_workspace_gateway
from backend.app.domain.execution_result import (
    BatchExecutionResult,
    ItemExecutionResult,
    summarize_execution,
)
from backend.app.domain.execution_result_store import ExecutionResultGateway, StoredExecutionResult
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/review/execution-results", tags=["review"])


class ItemExecutionPayload(BaseModel):
    item_id: str = Field(min_length=1, max_length=100)
    success: bool
    message: str = Field(min_length=1, max_length=500)


class ExecutionPayload(BaseModel):
    items: list[ItemExecutionPayload]


class StoredExecutionResultResponse(BaseModel):
    result_id: str
    workspace_id: str
    result: BatchExecutionResult
    created_at: datetime


@router.post("/summarize", response_model=BatchExecutionResult)
async def summarize(payload: ExecutionPayload) -> BatchExecutionResult:
    return summarize_execution([ItemExecutionResult(**item.model_dump()) for item in payload.items])


@router.post(
    "/store-workspaces/{workspace_id}",
    response_model=StoredExecutionResultResponse,
)
async def save_result(
    workspace_id: str,
    payload: ExecutionPayload,
    gateway: Annotated[ExecutionResultGateway, Depends(get_execution_result_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> StoredExecutionResult:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    result = summarize_execution(
        [ItemExecutionResult(**item.model_dump()) for item in payload.items]
    )
    return await gateway.save(workspace_id=workspace_id, result=result)


@router.get(
    "/store-workspaces/{workspace_id}",
    response_model=list[StoredExecutionResultResponse],
)
async def list_results(
    workspace_id: str,
    gateway: Annotated[ExecutionResultGateway, Depends(get_execution_result_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[StoredExecutionResult]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_results(workspace_id=workspace_id, limit=limit)
