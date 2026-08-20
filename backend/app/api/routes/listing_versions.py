"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_listing_version_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.listing_version import (
    ListingVersion,
    ListingVersionGateway,
    ListingVersionStatus,
    create_listing_version,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/versions", tags=["listing"])


class ListingVersionPayload(BaseModel):
    """说明 ListingVersionPayload 的职责、状态边界和对外协作关系。"""
    version: int
    original_text: str
    edited_text: str
    status: ListingVersionStatus = "draft"


@router.post("/compare", response_model=ListingVersion)
async def compare_listing_version(payload: ListingVersionPayload) -> ListingVersion:
    """执行 compare_listing_version 的业务流程并返回该流程的结果。"""
    return create_listing_version(**payload.model_dump())


@router.post("/store-workspaces/{workspace_id}/compare-and-save", response_model=ListingVersion)
async def compare_and_save_listing_version(
    workspace_id: str,
    payload: ListingVersionPayload,
    gateway: Annotated[ListingVersionGateway, Depends(get_listing_version_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ListingVersion:
    """执行 compare_and_save_listing_version 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    version = await compare_listing_version(payload)
    return await gateway.save_version(
        workspace_id=workspace_id, product_scope="listing", version=version
    )


@router.get("/store-workspaces/{workspace_id}", response_model=list[ListingVersion])
async def list_listing_versions(
    workspace_id: str,
    gateway: Annotated[ListingVersionGateway, Depends(get_listing_version_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[ListingVersion]:
    """执行 list_listing_versions 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_versions(
        workspace_id=workspace_id, product_scope="listing", limit=limit
    )
