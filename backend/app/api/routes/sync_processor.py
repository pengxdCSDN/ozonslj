"""说明本模块的职责、边界和主要协作对象。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/sync-processor", tags=["seller-api"])


class SyncProcessorPlanPayload(BaseModel):
    """说明 SyncProcessorPlanPayload 的职责、状态边界和对外协作关系。"""
    resource_type: str = Field(min_length=1)
    initial_cursor: str | None = None
    max_pages: int = Field(default=100, ge=1, le=1000)
    max_retries: int = Field(default=3, ge=0, le=10)


class SyncProcessorPlan(BaseModel):
    """说明 SyncProcessorPlan 的职责、状态边界和对外协作关系。"""
    resource_type: str
    initial_cursor: str | None
    max_pages: int
    max_retries: int
    dry_run: bool
    watermark_policy: str


@router.post("/plan", response_model=SyncProcessorPlan)
async def build_plan(payload: SyncProcessorPlanPayload) -> SyncProcessorPlan:
    """执行 build_plan 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if payload.resource_type not in {"products", "stock", "orders", "postings"}:
        raise HTTPException(
            status_code=422,
            detail={"code": "sync_resource_invalid", "message": "资源类型无效"},
        )
    return SyncProcessorPlan(
        resource_type=payload.resource_type,
        initial_cursor=payload.initial_cursor,
        max_pages=payload.max_pages,
        max_retries=payload.max_retries,
        dry_run=True,
        watermark_policy="仅在页面成功保存后推进；失败不推进长期水位",
    )
