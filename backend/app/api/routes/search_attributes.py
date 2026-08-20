"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_search_attributes_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.search_attributes import (
    SearchAttributesGateway,
    SearchAttributesReport,
    build_search_attributes,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/listing/search-attributes", tags=["listing"])


class SearchAttributesPayload(BaseModel):
    """说明 SearchAttributesPayload 的职责、状态边界和对外协作关系。"""
    required: dict[str, str]
    current: dict[str, str] = {}
    keyword_terms: dict[str, str] = {}


@router.post("/suggest", response_model=SearchAttributesReport)
async def suggest_search_attributes(payload: SearchAttributesPayload) -> SearchAttributesReport:
    """执行 suggest_search_attributes 的业务流程并返回该流程的结果。"""
    return build_search_attributes(payload.required, payload.current, payload.keyword_terms)


@router.post(
    "/store-workspaces/{workspace_id}/suggest-and-save",
    response_model=SearchAttributesReport,
)
async def suggest_and_save_search_attributes(
    workspace_id: str,
    payload: SearchAttributesPayload,
    gateway: Annotated[SearchAttributesGateway, Depends(get_search_attributes_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SearchAttributesReport:
    """执行 suggest_and_save_search_attributes 的业务流程并返回该流程的结果。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    report = build_search_attributes(payload.required, payload.current, payload.keyword_terms)
    return await gateway.save_report(
        workspace_id=workspace_id,
        product_scope=payload.required.get("product_scope", "current"),
        report=report,
    )


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[SearchAttributesReport])
async def list_search_attributes_history(
    workspace_id: str,
    gateway: Annotated[SearchAttributesGateway, Depends(get_search_attributes_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[SearchAttributesReport]:
    """返回属性建议历史，供运营复核覆盖率和缺失必填项。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_reports(workspace_id=workspace_id, limit=limit)
