"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.dependencies import (
    get_stock_position_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.stock_position import StockPositionGateway, StockPositionPage
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["stock-positions"])


@router.get("/{workspace_id}/stock-positions", response_model=StockPositionPage)
async def list_stock_positions(
    workspace_id: str,
    gateway: Annotated[StockPositionGateway, Depends(get_stock_position_gateway)],
    workspace_gateway: Annotated[
        StoreWorkspaceGateway,
        Depends(get_store_workspace_gateway),
    ],
    cursor: Annotated[str | None, Query(pattern=r"^\d+$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StockPositionPage:
    """返回已同步库存，未验证或停用工作区不得读取业务事实。"""
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "workspace_not_found", "message": "工作区不存在"},
        )
    if workspace.status == "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "workspace_pending", "message": "工作区尚未验证"},
        )
    if workspace.status == "invalid":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "workspace_invalid", "message": "工作区凭据无效"},
        )
    if workspace.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "workspace_disabled", "message": "工作区已停用"},
        )
    return await gateway.list_stock_positions(
        workspace_id=workspace_id,
        cursor=cursor,
        limit=limit,
    )
