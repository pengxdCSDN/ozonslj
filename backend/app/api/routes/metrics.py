from fastapi import APIRouter, Response

from backend.app.infrastructure.observability import METRICS, update_resource_metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """返回无用户标识的聚合指标；Nginx 不对公网代理该路径。"""
    update_resource_metrics()
    return Response(content=METRICS.render(), media_type="text/plain; version=0.0.4")
