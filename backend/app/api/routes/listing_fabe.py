from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_listing_fabe_gateway, get_store_workspace_gateway
from backend.app.domain.listing_fabe import (
    FabePoint,
    ListingFabeDraft,
    ListingFabeGateway,
    generate_fabe_draft,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/fabe", tags=["listing"])


class FabePointPayload(BaseModel):
    feature: str
    advantage: str
    benefit: str
    evidence: str | None = None
    copy_text: str = Field(alias="copy")


class FabePayload(BaseModel):
    product_name: str
    points: list[FabePointPayload]


@router.post("/generate", response_model=ListingFabeDraft)
async def generate_fabe(payload: FabePayload) -> ListingFabeDraft:
    return generate_fabe_draft(
        [
            FabePoint(
                point.feature,
                point.advantage,
                point.benefit,
                point.evidence,
                point.copy_text,
            )
            for point in payload.points
        ],
        product_name=payload.product_name,
    )


@router.post("/store-workspaces/{workspace_id}/generate-and-save", response_model=ListingFabeDraft)
async def generate_and_save_fabe(
    workspace_id: str,
    payload: FabePayload,
    gateway: Annotated[ListingFabeGateway, Depends(get_listing_fabe_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> ListingFabeDraft:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    draft = await generate_fabe(payload)
    return await gateway.save_draft(
        workspace_id=workspace_id, product_scope=payload.product_name, draft=draft
    )


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ListingFabeDraft])
async def list_fabe_history(
    workspace_id: str,
    gateway: Annotated[ListingFabeGateway, Depends(get_listing_fabe_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ListingFabeDraft]:
    """返回 FABE 草稿历史，供人工编辑卖点和补齐证据。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_drafts(workspace_id=workspace_id, limit=limit)
