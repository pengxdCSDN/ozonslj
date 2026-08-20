"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_quality_finding_gateway, get_store_workspace_gateway
from backend.app.domain.data_quality import QualityFinding, QualityFindingGateway
from backend.app.domain.money_inventory_quality import MoneyInventoryFinding, check_money_inventory
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])


class MoneyInventoryPayload(BaseModel):
    """说明 MoneyInventoryPayload 的职责、状态边界和对外协作关系。"""
    record: dict[str, object]
    allowed_currencies: set[str] = Field(default_factory=lambda: {"RUB", "CNY", "USD", "EUR"})


@router.post("/money-inventory-check", response_model=list[MoneyInventoryFinding])
async def money_inventory_check(payload: MoneyInventoryPayload) -> list[MoneyInventoryFinding]:
    """执行 money_inventory_check 的业务流程并返回该流程的结果。"""
    return check_money_inventory(payload.record, allowed_currencies=payload.allowed_currencies)


@router.post(
    "/store-workspaces/{workspace_id}/money-inventory-check-and-isolate",
    response_model=list[MoneyInventoryFinding],
)
async def money_inventory_check_and_isolate(
    workspace_id: str,
    payload: MoneyInventoryPayload,
    gateway: Annotated[QualityFindingGateway, Depends(get_quality_finding_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[MoneyInventoryFinding]:
    """将币种、金额和库存异常写入质量隔离区，阻止其静默进入运营指标。"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    findings = await money_inventory_check(payload)
    isolated = [QualityFinding(
        rule_code=item.rule_code, field_name=item.field,
        severity="error", message=item.message,
    ) for item in findings]
    if isolated:
        await gateway.create_findings(workspace_id=workspace_id, findings=isolated)
    return findings
