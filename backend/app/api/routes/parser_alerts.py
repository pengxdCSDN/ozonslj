"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.dependencies import get_parser_alert_gateway, get_store_workspace_gateway
from backend.app.domain.parser_alert import ParserAlertGateway, ParserChange, detect_parser_changes
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/parser-alerts", tags=["parser-alerts"])


class ParserComparisonPayload(BaseModel):
    """说明 ParserComparisonPayload 的职责、状态边界和对外协作关系。"""
    url: str = ""
    previous: dict[str, str | None]
    current: dict[str, str | None]


@router.post("/compare", response_model=list[ParserChange])
async def compare_parser_results(payload: ParserComparisonPayload) -> list[ParserChange]:
    """执行 compare_parser_results 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return detect_parser_changes(payload.previous, payload.current)


@router.post("/store-workspaces/{workspace_id}/compare-and-save", response_model=list[ParserChange])
async def compare_and_save_parser_results(
    workspace_id: str,
    payload: ParserComparisonPayload,
    gateway: Annotated[ParserAlertGateway, Depends(get_parser_alert_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[ParserChange]:
    """执行 compare_and_save_parser_results 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    changes = detect_parser_changes(payload.previous, payload.current)
    return await gateway.create_alerts(workspace_id=workspace_id, url=payload.url, changes=changes)


@router.get("/store-workspaces/{workspace_id}/history", response_model=list[ParserChange])
async def list_parser_alert_history(
    workspace_id: str,
    gateway: Annotated[ParserAlertGateway, Depends(get_parser_alert_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[ParserChange]:
    """返回字段级解析告警历史，不返回原始页面内容。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.list_alerts(workspace_id=workspace_id, limit=limit)
