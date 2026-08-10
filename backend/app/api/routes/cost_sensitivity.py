from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_cost_sensitivity_gateway, get_store_workspace_gateway
from backend.app.domain.assumption_version import assumption_version
from backend.app.domain.cost_sensitivity import (
    CostSensitivityGateway,
    CostSensitivityInput,
    CostSensitivityScenario,
    analyze_cost_sensitivity,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/selection/cost-sensitivity", tags=["selection"])


class CostSensitivityPayload(BaseModel):
    selling_price_minor: int = Field(ge=0)
    purchase_cost_minor: int = Field(ge=0)
    logistics_cost_minor: int = Field(ge=0)
    commission_minor: int = Field(ge=0)
    ad_cost_minor: int = Field(ge=0)
    return_loss_minor: int = Field(ge=0)


@router.post("/analyze", response_model=list[CostSensitivityScenario])
async def analyze_costs(payload: CostSensitivityPayload) -> list[CostSensitivityScenario]:
    return list(analyze_cost_sensitivity(CostSensitivityInput(**payload.model_dump())))


@router.post(
    "/store-workspaces/{workspace_id}/analyze-and-save",
    response_model=list[CostSensitivityScenario],
)
async def analyze_and_save_costs(
    workspace_id: str,
    payload: CostSensitivityPayload,
    gateway: Annotated[CostSensitivityGateway, Depends(get_cost_sensitivity_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[CostSensitivityScenario]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    assumptions = payload.model_dump()
    assumptions["assumption_version"] = assumption_version(assumptions)
    scenarios = analyze_cost_sensitivity(CostSensitivityInput(**assumptions))
    return list(await gateway.save_analysis(
        workspace_id=workspace_id, assumptions=assumptions, scenarios=scenarios
    ))
