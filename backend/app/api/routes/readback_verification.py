from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_readback_verification_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.readback_store import (
    ReadbackVerificationGateway,
    StoredReadbackVerification,
)
from backend.app.domain.readback_verification import ReadbackVerification, verify_readback
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/review/readback", tags=["review"])


class ReadbackPayload(BaseModel):
    expected: dict[str, object] = Field(default_factory=dict)
    actual: dict[str, object] = Field(default_factory=dict)


class StoredReadbackResponse(BaseModel):
    verification_id: str
    workspace_id: str
    verification: ReadbackVerification
    created_at: datetime


@router.post("/verify", response_model=ReadbackVerification)
async def verify(payload: ReadbackPayload) -> ReadbackVerification:
    return verify_readback(**payload.model_dump())


@router.post("/store-workspaces/{workspace_id}", response_model=StoredReadbackResponse)
async def save_verification(
    workspace_id: str,
    payload: ReadbackPayload,
    gateway: Annotated[ReadbackVerificationGateway, Depends(get_readback_verification_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> StoredReadbackVerification:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.save(
        workspace_id=workspace_id, verification=verify_readback(**payload.model_dump())
    )


@router.get("/store-workspaces/{workspace_id}", response_model=list[StoredReadbackResponse])
async def list_verifications(
    workspace_id: str,
    gateway: Annotated[ReadbackVerificationGateway, Depends(get_readback_verification_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[StoredReadbackVerification]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_results(workspace_id=workspace_id, limit=limit)
