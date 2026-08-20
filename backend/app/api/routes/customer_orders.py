"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.dependencies import (
    get_customer_order_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.customer_order import CustomerOrderGateway, CustomerOrderPage
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["customer-orders"])


@router.get("/{workspace_id}/customer-orders", response_model=CustomerOrderPage)
async def list_customer_orders(
    workspace_id: str,
    gateway: Annotated[CustomerOrderGateway, Depends(get_customer_order_gateway)],
    workspace_gateway: Annotated[
        StoreWorkspaceGateway,
        Depends(get_store_workspace_gateway),
    ],
    cursor: Annotated[str | None, Query(pattern=r"^\d+$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CustomerOrderPage:
    """返回已同步的脱敏订单摘要，不在请求线程访问 Ozon。"""
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
    return await gateway.list_customer_orders(
        workspace_id=workspace_id,
        cursor=cursor,
        limit=limit,
    )
