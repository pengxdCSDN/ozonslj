from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_store_workspace_gateway
from backend.app.domain.store_workspace import StoreWorkspaceGateway, StoreWorkspaceList

router = APIRouter(prefix="/v1/store-workspaces", tags=["store-workspaces"])


@router.get("", response_model=StoreWorkspaceList)
async def list_store_workspaces(
    gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> StoreWorkspaceList:
    return StoreWorkspaceList(items=await gateway.list_store_workspaces())
