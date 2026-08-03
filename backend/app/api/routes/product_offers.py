from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.dependencies import get_current_user, get_product_offer_gateway
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.product_offer import ProductOfferPage
from backend.app.domain.store_workspace import WorkspaceNotFoundError
from backend.app.infrastructure.ozon.gateway import ProductOfferGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["product-offers"])


@router.get("/{workspace_id}/product-offers", response_model=ProductOfferPage)
async def list_product_offers(
    workspace_id: str,
    gateway: Annotated[ProductOfferGateway, Depends(get_product_offer_gateway)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    cursor: Annotated[str | None, Query(pattern=r"^\d+$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductOfferPage:
    if workspace_id not in user.workspace_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该工作区")
    try:
        return await gateway.list_product_offers(
            workspace_id=workspace_id,
            cursor=cursor,
            limit=limit,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store workspace not found",
        ) from error
