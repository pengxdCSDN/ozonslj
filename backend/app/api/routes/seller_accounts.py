"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_current_user, get_seller_account_service
from backend.app.application.seller_accounts import SellerAccountService
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.seller_account import (
    CreatedSellerAccount,
    SellerAccountConflictError,
    SellerCredentialValidationError,
)

router = APIRouter(prefix="/v1/seller-accounts", tags=["seller-accounts"])


class CreateSellerAccountRequest(BaseModel):
    """说明 CreateSellerAccountRequest 的职责、状态边界和对外协作关系。"""
    display_name: str = Field(min_length=1, max_length=120)
    workspace_name: str = Field(min_length=1, max_length=120)
    client_id: str = Field(min_length=1, max_length=200)
    api_key: str = Field(min_length=1, max_length=500)


@router.post("", response_model=CreatedSellerAccount, status_code=status.HTTP_201_CREATED)
async def create_seller_account(
    request_body: CreateSellerAccountRequest,
    service: Annotated[SellerAccountService, Depends(get_seller_account_service)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CreatedSellerAccount:
    """执行 create_seller_account 的业务流程并返回该流程的结果。

Args:
    request_body: 参数语义、输入边界和安全约束。
    service: 参数语义、输入边界和安全约束。
    user: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可添加卖家账号")
    try:
        return await service.create(
            operator_id=user.id,
            display_name=request_body.display_name,
            workspace_name=request_body.workspace_name,
            client_id=request_body.client_id,
            api_key=request_body.api_key,
        )
    except SellerCredentialValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except SellerAccountConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
