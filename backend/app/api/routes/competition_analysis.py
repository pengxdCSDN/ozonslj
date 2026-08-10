from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_competition_analysis_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.competition_analysis import (
    CompetitionAnalysis,
    CompetitionAnalysisGateway,
    CompetitorObservation,
    analyze_competition,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/selection/competition", tags=["selection"])


class CompetitorPayload(BaseModel):
    seller: str
    brand: str | None = None
    price_minor: int = Field(ge=0)
    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)


class CompetitionPayload(BaseModel):
    items: list[CompetitorPayload]


@router.post("/analyze", response_model=CompetitionAnalysis)
async def analyze_competitors(payload: CompetitionPayload) -> CompetitionAnalysis:
    return analyze_competition(
        [CompetitorObservation(**item.model_dump()) for item in payload.items]
    )


@router.post(
    "/store-workspaces/{workspace_id}/analyze-and-save",
    response_model=CompetitionAnalysis,
)
async def analyze_and_save_competitors(
    workspace_id: str,
    payload: CompetitionPayload,
    gateway: Annotated[CompetitionAnalysisGateway, Depends(get_competition_analysis_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> CompetitionAnalysis:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    analysis = analyze_competition(
        [CompetitorObservation(**item.model_dump()) for item in payload.items]
    )
    return await gateway.save_analysis(workspace_id=workspace_id, analysis=analysis)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[CompetitionAnalysis])
async def list_competition_history(
    workspace_id: str,
    gateway: Annotated[CompetitionAnalysisGateway, Depends(get_competition_analysis_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[CompetitionAnalysis]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_analyses(workspace_id=workspace_id, limit=limit)
