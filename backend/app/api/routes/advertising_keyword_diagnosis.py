from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_advertising_keyword_diagnosis_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.advertising_keyword_diagnosis import (
    AdvertisingKeywordDiagnosis,
    AdvertisingKeywordDiagnosisGateway,
    diagnose_keywords,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/advertising/keywords", tags=["advertising"])


class KeywordDiagnosisPayload(BaseModel):
    rows: list[dict[str, object]] = Field(min_length=1)
    min_impressions: int = Field(default=100, ge=0)
    min_clicks: int = Field(default=10, ge=0)
    high_cvr_percent: float = Field(default=8.0, ge=0)
    high_spend_minor: int = Field(default=1000, ge=0)


@router.post("/diagnose", response_model=list[AdvertisingKeywordDiagnosis])
async def diagnose(payload: KeywordDiagnosisPayload) -> list[AdvertisingKeywordDiagnosis]:
    try:
        return diagnose_keywords(
            payload.rows,
            min_impressions=payload.min_impressions,
            min_clicks=payload.min_clicks,
            high_cvr_percent=payload.high_cvr_percent,
            high_spend_minor=payload.high_spend_minor,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "keyword_diagnosis_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/diagnose-and-save",
    response_model=list[AdvertisingKeywordDiagnosis],
)
async def diagnose_and_save(
    workspace_id: str,
    payload: KeywordDiagnosisPayload,
    gateway: Annotated[
        AdvertisingKeywordDiagnosisGateway,
        Depends(get_advertising_keyword_diagnosis_gateway),
    ],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[AdvertisingKeywordDiagnosis]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    diagnoses = await diagnose(payload)
    return await gateway.save_report(workspace_id=workspace_id, diagnoses=diagnoses)


@router.get(
    "/store-workspaces/{workspace_id}/reports",
    response_model=list[list[AdvertisingKeywordDiagnosis]],
)
async def list_reports(
    workspace_id: str,
    gateway: Annotated[
        AdvertisingKeywordDiagnosisGateway,
        Depends(get_advertising_keyword_diagnosis_gateway),
    ],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 20,
) -> list[list[AdvertisingKeywordDiagnosis]]:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_limit"})
    return await gateway.list_reports(workspace_id=workspace_id, limit=limit)
