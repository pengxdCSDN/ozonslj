"""说明本模块的职责、边界和主要协作对象。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_credential_protector,
    get_ozon_product_catalog_gateway,
    get_seller_product_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.ozon_product_catalog import (
    OzonProductCatalogGateway,
    ProductCatalogPage,
)
from backend.app.domain.seller_product_snapshot import SellerProductSnapshotGateway
from backend.app.domain.seller_product_sync import (
    SellerProductSyncPreview,
    map_seller_product_response,
)
from backend.app.domain.store_workspace import (
    CredentialProtector,
    OzonAuthenticationError,
    OzonCredentials,
    OzonMalformedResponseError,
    OzonPermissionError,
    OzonRateLimitError,
    OzonTemporaryError,
    StoreWorkspaceGateway,
)

router = APIRouter(prefix="/v1/seller/products", tags=["seller-api"])


class SellerProductSyncPayload(BaseModel):
    """说明 SellerProductSyncPayload 的职责、状态边界和对外协作关系。"""
    response: dict[str, object]
    cursor: str | None = None


@router.get("/store-workspaces/{workspace_id}/catalog", response_model=ProductCatalogPage)
async def read_ozon_catalog(
    workspace_id: str,
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    catalog_gateway: Annotated[
        OzonProductCatalogGateway,
        Depends(get_ozon_product_catalog_gateway),
    ],
    protector: Annotated[CredentialProtector, Depends(get_credential_protector)],
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> ProductCatalogPage:
    """从后端凭据边界读取一页 Ozon 商品、规格和价格佣金。

    Args:
        workspace_id: 当前已授权店铺工作区编号。
        workspace_gateway: 读取工作区状态和加密凭据的端口。
        catalog_gateway: Ozon 商品只读适配器。
        protector: 解密后端保存的 Api-Key，不向响应或日志暴露。
        cursor: Ozon 商品接口分页游标，可为空表示第一页。
        limit: 单页 SKU 数量，范围为 1～100。

    Returns:
        标准化商品目录页面，字段缺失以 null 返回供前端提示补录。

    Raises:
        HTTPException: 工作区不存在、未验证、凭据损坏或 Ozon 读取失败时抛出。
    """
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    loaded = await workspace_gateway.load_credentials(workspace_id)
    if loaded is None:
        raise HTTPException(status_code=409, detail={"code": "ozon_credentials_missing"})
    client_id, encrypted_api_key, credential_version = loaded
    try:
        api_key = protector.unprotect(encrypted_api_key, credential_version=credential_version)
        return await catalog_gateway.list_skus(
            credentials=OzonCredentials(client_id=client_id, api_key=api_key),
            cursor=cursor,
            limit=limit,
        )
    except (OzonAuthenticationError, OzonPermissionError) as error:
        raise HTTPException(
            status_code=403,
            detail={"code": "ozon_catalog_forbidden", "message": str(error)},
        ) from error
    except OzonRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail={"code": "ozon_catalog_rate_limited", "message": str(error)},
        ) from error
    except (OzonTemporaryError, OzonMalformedResponseError) as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "ozon_catalog_unavailable", "message": str(error)},
        ) from error


@router.post("/sync-preview", response_model=SellerProductSyncPreview)
async def sync_preview(payload: SellerProductSyncPayload) -> SellerProductSyncPreview:
    """执行 sync_preview 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    try:
        return map_seller_product_response(payload.response, cursor=payload.cursor)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_product_response_invalid", "message": str(error)},
        ) from error


@router.post(
    "/store-workspaces/{workspace_id}/sync-and-save",
    response_model=SellerProductSyncPreview,
)
async def sync_and_save(
    workspace_id: str,
    payload: SellerProductSyncPayload,
    gateway: Annotated[SellerProductSnapshotGateway, Depends(get_seller_product_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> SellerProductSyncPreview:
    """执行 sync_and_save 的业务流程并返回该流程的结果。

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
    try:
        preview = map_seller_product_response(payload.response, cursor=payload.cursor)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "seller_product_response_invalid", "message": str(error)},
        ) from error
    return await gateway.save_snapshot(workspace_id=workspace_id, preview=preview)


@router.get(
    "/store-workspaces/{workspace_id}/snapshots",
    response_model=list[SellerProductSyncPreview],
)
async def list_snapshots(
    workspace_id: str,
    gateway: Annotated[SellerProductSnapshotGateway, Depends(get_seller_product_snapshot_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SellerProductSyncPreview]:
    """执行 list_snapshots 的业务流程并返回该流程的结果。

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
    return await gateway.list_snapshots(workspace_id=workspace_id, limit=limit)
