"""说明本模块的职责、边界和主要协作对象。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.erp_adapter import ErpSupplyRecord, parse_erp_csv

router = APIRouter(prefix="/v1/erp", tags=["erp"])


class ErpCsvPreviewPayload(BaseModel):
    """说明 ErpCsvPreviewPayload 的职责、状态边界和对外协作关系。"""
    content: str = Field(min_length=1, max_length=2_000_000)


@router.post("/csv/preview", response_model=list[ErpSupplyRecord])
async def preview_csv(payload: ErpCsvPreviewPayload) -> list[ErpSupplyRecord]:
    """执行 preview_csv 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return parse_erp_csv(payload.content)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "erp_csv_invalid", "message": str(error)},
        ) from error
