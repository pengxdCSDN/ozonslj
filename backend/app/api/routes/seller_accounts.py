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
