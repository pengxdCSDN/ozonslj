from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_selection_decision_book_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.selection_decision_book import (
    SelectionDecisionBook,
    SelectionDecisionBookGateway,
    validate_confirmation_status,
    validate_decision_book,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/selection/decision-books", tags=["selection"])


class DecisionBookPayload(BaseModel):
    opportunity_summary: str
    customer_scene: str
    market_sample: str
    competitor_snapshots: list[str] = Field(default_factory=list)
    profit_calculation: str
    risks: list[str] = Field(default_factory=list)
    price_range: str
    stock_recommendation: str
    seed_keywords: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    uncertainty: str
    confirmation_status: str = "pending"


@router.post(
    "/store-workspaces/{workspace_id}/generate-and-save",
    response_model=DecisionBookPayload,
)
async def generate_and_save_decision_book(
    workspace_id: str,
    payload: DecisionBookPayload,
    gateway: Annotated[SelectionDecisionBookGateway, Depends(get_selection_decision_book_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> DecisionBookPayload:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if payload.confirmation_status not in {"pending", "confirmed", "rejected"}:
        raise HTTPException(status_code=422, detail={"code": "confirmation_status_invalid"})
    book = SelectionDecisionBook(
        opportunity_summary=payload.opportunity_summary,
        customer_scene=payload.customer_scene,
        market_sample=payload.market_sample,
        competitor_snapshots=tuple(payload.competitor_snapshots),
        profit_calculation=payload.profit_calculation,
        risks=tuple(payload.risks),
        price_range=payload.price_range,
        stock_recommendation=payload.stock_recommendation,
        seed_keywords=tuple(payload.seed_keywords),
        data_sources=tuple(payload.data_sources),
        uncertainty=payload.uncertainty,
        confirmation_status=payload.confirmation_status,
    )
    try:
        validate_decision_book(book)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "decision_book_incomplete", "message": str(error)},
        ) from error
    await gateway.save_book(workspace_id=workspace_id, book=book)
    return payload


@router.post(
    "/store-workspaces/{workspace_id}/confirm",
    response_model=DecisionBookPayload,
)
async def confirm_decision_book(
    workspace_id: str,
    payload: DecisionBookPayload,
    gateway: Annotated[SelectionDecisionBookGateway, Depends(get_selection_decision_book_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> DecisionBookPayload:
    """记录人工确认结果；不调用采购、上架或广告写适配器。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        validate_confirmation_status(payload.confirmation_status)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "confirmation_required"}) from error
    book = SelectionDecisionBook(
        opportunity_summary=payload.opportunity_summary,
        customer_scene=payload.customer_scene,
        market_sample=payload.market_sample,
        competitor_snapshots=tuple(payload.competitor_snapshots),
        profit_calculation=payload.profit_calculation,
        risks=tuple(payload.risks),
        price_range=payload.price_range,
        stock_recommendation=payload.stock_recommendation,
        seed_keywords=tuple(payload.seed_keywords),
        data_sources=tuple(payload.data_sources),
        uncertainty=payload.uncertainty,
        confirmation_status=payload.confirmation_status,
    )
    try:
        validate_decision_book(book)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "decision_book_incomplete", "message": str(error)},
        ) from error
    await gateway.save_book(workspace_id=workspace_id, book=book)
    return payload


@router.get(
    "/store-workspaces/{workspace_id}",
    response_model=list[DecisionBookPayload],
)
async def list_decision_books(
    workspace_id: str,
    gateway: Annotated[SelectionDecisionBookGateway, Depends(get_selection_decision_book_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[SelectionDecisionBook]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_books(workspace_id=workspace_id, limit=limit)
