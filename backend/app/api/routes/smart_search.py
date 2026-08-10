from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_smart_search_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.smart_search import (
    SmartSearchGateway,
    SmartSearchReport,
    check_smart_search,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/smart-search", tags=["listing"])


class SmartSearchPayload(BaseModel):
    text: str
    required_terms: list[str]
    category: str
    category_terms: list[str] = []


@router.post("/check", response_model=SmartSearchReport)
async def smart_search_check(payload: SmartSearchPayload) -> SmartSearchReport:
    return check_smart_search(
        payload.text,
        required_terms=payload.required_terms,
        category=payload.category,
        category_terms=payload.category_terms,
    )


@router.post("/store-workspaces/{workspace_id}/check-and-save", response_model=SmartSearchReport)
async def check_and_save_smart_search(
    workspace_id: str,
    payload: SmartSearchPayload,
    gateway: Annotated[SmartSearchGateway, Depends(get_smart_search_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SmartSearchReport:
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    report = await smart_search_check(payload)
    return await gateway.save_report(
        workspace_id=workspace_id, product_scope=payload.category,
        source_text=payload.text, report=report,
    )


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[SmartSearchReport])
async def list_smart_search_history(
    workspace_id: str,
    gateway: Annotated[SmartSearchGateway, Depends(get_smart_search_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[SmartSearchReport]:
    """返回 Smart Search 检查历史，供人工复核建议且保留原文。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_reports(workspace_id=workspace_id, limit=limit)
