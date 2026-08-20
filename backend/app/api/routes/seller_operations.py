"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.dependencies import (
    get_seller_operation_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.seller_operation import SellerOperationGateway, SellerOperationPage
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["seller-operations"])


@router.get("/{workspace_id}/seller-operations", response_model=SellerOperationPage)
async def list_seller_operations(
    workspace_id: str,
    gateway: Annotated[SellerOperationGateway, Depends(get_seller_operation_gateway)],
    workspace_gateway: Annotated[
        StoreWorkspaceGateway,
        Depends(get_store_workspace_gateway),
    ],
    cursor: Annotated[str | None, Query(pattern=r"^\d+$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SellerOperationPage:
    """返回固定白名单的只读审计时间线。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
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
    return await gateway.list_seller_operations(
        workspace_id=workspace_id,
        cursor=cursor,
        limit=limit,
    )
