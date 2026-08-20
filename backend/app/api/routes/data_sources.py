"""说明本模块的职责、边界和主要协作对象。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.data_source import DataSourceLabel, get_data_source_label

router = APIRouter(prefix="/v1/data-sources", tags=["data-quality"])


class DataSourcePayload(BaseModel):
    """说明 DataSourcePayload 的职责、状态边界和对外协作关系。"""
    source: str = Field(min_length=1)


@router.post("/label", response_model=DataSourceLabel)
async def label_source(payload: DataSourcePayload) -> DataSourceLabel:
    """执行 label_source 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return get_data_source_label(payload.source)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "data_source_invalid", "message": str(error)},
        ) from error
