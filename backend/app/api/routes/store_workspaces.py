from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_current_user, get_store_workspace_gateway
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.store_workspace import StoreWorkspaceGateway, StoreWorkspaceList

router = APIRouter(prefix="/v1/store-workspaces", tags=["store-workspaces"])


@router.get("", response_model=StoreWorkspaceList)
async def list_store_workspaces(
    gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> StoreWorkspaceList:
    return StoreWorkspaceList(items=await gateway.list_store_workspaces(user.workspace_ids))
