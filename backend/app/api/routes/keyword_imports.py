"""说明本模块的职责、边界和主要协作对象。"""

import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_keyword_import_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.keyword_import import (
    KeywordImportBatch,
    KeywordImportError,
    KeywordImportGateway,
    KeywordImportRow,
    keyword_import_bytes_fingerprint,
    keyword_import_fingerprint,
    parse_keyword_csv,
    parse_keyword_xlsx,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["keyword-imports"])


class KeywordImportPreview(BaseModel):
    """说明 KeywordImportPreview 的职责、状态边界和对外协作关系。"""
    rows: list[KeywordImportRow]
    total: int
    fingerprint: str


class MappedKeywordImportRequest(BaseModel):
    """说明 MappedKeywordImportRequest 的职责、状态边界和对外协作关系。"""
    content: str
    column_mapping: dict[str, str]


class MappedXlsxKeywordImportRequest(BaseModel):
    """说明 MappedXlsxKeywordImportRequest 的职责、状态边界和对外协作关系。"""
    content_base64: str
    column_mapping: dict[str, str]


class CommitKeywordImportRequest(BaseModel):
    """说明 CommitKeywordImportRequest 的职责、状态边界和对外协作关系。"""
    fingerprint: str
    rows: list[KeywordImportRow]


@router.post("/{workspace_id}/keyword-report-imports/preview", response_model=KeywordImportPreview)
async def preview_keyword_import(
    workspace_id: str,
    request: Request,
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> KeywordImportPreview:
    """执行 preview_keyword_import 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    request: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "workspace_not_found"},
        )
    if workspace.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "workspace_not_active"},
        )
    content = (await request.body()).decode("utf-8-sig")
    try:
        rows = parse_keyword_csv(content)
    except (UnicodeDecodeError, KeywordImportError) as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "keyword_import_invalid", "message": str(error)},
        ) from error
    return KeywordImportPreview(
        rows=rows, total=len(rows), fingerprint=keyword_import_fingerprint(content)
    )


@router.post(
    "/{workspace_id}/keyword-report-imports/preview-mapped",
    response_model=KeywordImportPreview,
)
async def preview_mapped_keyword_import(
    workspace_id: str,
    payload: MappedKeywordImportRequest,
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> KeywordImportPreview:
    """执行 preview_mapped_keyword_import 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        rows = parse_keyword_csv(payload.content, payload.column_mapping)
    except KeywordImportError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "keyword_import_invalid", "message": str(error)},
        ) from error
    return KeywordImportPreview(
        rows=rows,
        total=len(rows),
        fingerprint=keyword_import_fingerprint(payload.content),
    )


@router.post(
    "/{workspace_id}/keyword-report-imports/preview-xlsx",
    response_model=KeywordImportPreview,
)
async def preview_xlsx_keyword_import(
    workspace_id: str,
    request: Request,
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> KeywordImportPreview:
    """执行 preview_xlsx_keyword_import 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    request: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    content = await request.body()
    try:
        rows = parse_keyword_xlsx(content)
    except KeywordImportError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "keyword_import_invalid", "message": str(error)},
        ) from error
    return KeywordImportPreview(
        rows=rows,
        total=len(rows),
        fingerprint=keyword_import_bytes_fingerprint(content),
    )


@router.post(
    "/{workspace_id}/keyword-report-imports/preview-xlsx-mapped",
    response_model=KeywordImportPreview,
)
async def preview_mapped_xlsx_keyword_import(
    workspace_id: str,
    payload: MappedXlsxKeywordImportRequest,
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> KeywordImportPreview:
    """执行 preview_mapped_xlsx_keyword_import 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
        rows = parse_keyword_xlsx(content, payload.column_mapping)
    except (ValueError, KeywordImportError) as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "keyword_import_invalid", "message": str(error)},
        ) from error
    return KeywordImportPreview(
        rows=rows,
        total=len(rows),
        fingerprint=keyword_import_bytes_fingerprint(content),
    )


@router.post(
    "/{workspace_id}/keyword-report-imports",
    response_model=KeywordImportBatch,
    status_code=201,
)
async def commit_keyword_import(
    workspace_id: str,
    payload: CommitKeywordImportRequest,
    gateway: Annotated[KeywordImportGateway, Depends(get_keyword_import_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> KeywordImportBatch:
    """执行 commit_keyword_import 的业务流程并返回该流程的结果。

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
    workspace = await workspace_gateway.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    return await gateway.create_batch(
        workspace_id=workspace_id, fingerprint=payload.fingerprint, rows=payload.rows
    )


@router.get(
    "/{workspace_id}/keyword-report-imports/history",
    response_model=list[KeywordImportBatch],
)
async def list_keyword_import_history(
    workspace_id: str,
    gateway: Annotated[KeywordImportGateway, Depends(get_keyword_import_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
    limit: int = 50,
) -> list[KeywordImportBatch]:
    """返回导入批次指纹历史，支持确认重复文件未生成重复批次。

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
    return await gateway.list_batches(workspace_id=workspace_id, limit=limit)
