"""生产用 RAG 模型供应商维护 API。

所有写操作要求组织管理员权限。API Key 只在请求进入后端的短生命周期中出现，
随后写入受限 Secret 卷，响应只返回配置状态和末四位掩码。
"""

from __future__ import annotations

from typing import Annotated, Literal, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_model_credential_store,
    get_rag_model_provider_gateway,
    require_account_manager,
)
from backend.app.infrastructure.cloud_models import (
    CloudModelError,
    CloudModelQuotaError,
    DashScopeEmbeddingClient,
    OpenAICompatibleTranslationClient,
)
from backend.app.infrastructure.model_credentials import ModelCredentialStore
from backend.app.infrastructure.postgresql.rag_model_providers import (
    PostgresRagModelProviderGateway,
)

router = APIRouter(prefix="/v1/model-providers/managed", tags=["rag-model-providers"])
# 适配器名称不限定为内置供应商清单，便于接入任意 OpenAI-compatible 服务。
# 具体协议能力由连接测试和运行时客户端决定，数据库只校验名称非空。
ManagedAdapter = str
ManagedModelKind = Literal["embedding", "text"]
ManagedPurpose = Literal[
    "embedding", "translation", "intent_rewrite", "rerank", "answer_generation"
]


class ManagedProviderPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    adapter_type: ManagedAdapter = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=160)
    base_url: str = Field(min_length=12, max_length=500)
    model_kind: ManagedModelKind = "text"
    api_key: str | None = Field(default=None, min_length=1, max_length=500, repr=False)
    priority: int = Field(default=100, ge=1, le=1000)
    enabled: bool | None = None


class ManagedProviderResponse(BaseModel):
    provider_id: str
    name: str
    adapter_type: ManagedAdapter
    model: str
    base_url: str
    model_kind: ManagedModelKind
    priority: int
    enabled: bool
    credential_configured: bool
    credential_mask: str


class ManagedBindingPayload(BaseModel):
    primary_provider_id: str
    # 备用链按优先级排列，允许配置多个候选；运行时遇到限额、超时或不可用会逐个尝试。
    fallback_provider_ids: list[str] = Field(default_factory=list, max_length=20)


class ManagedBindingResponse(BaseModel):
    purpose: ManagedPurpose
    primary_provider_id: str
    fallback_provider_ids: list[str]
    revision: int


class ConnectivityTestPayload(BaseModel):
    purpose: Literal["embedding", "translation"]
    adapter_type: ManagedAdapter
    model: str = Field(min_length=1, max_length=160)
    base_url: str = Field(min_length=12, max_length=500)
    api_key: str = Field(min_length=1, max_length=500, repr=False)


class ConnectivityTestResponse(BaseModel):
    ok: bool
    status: Literal["reachable", "quota_exceeded", "failed"]
    message: str
    model: str


@router.get("/catalog")
async def model_provider_catalog(
    _account_manager: Annotated[object, Depends(require_account_manager)],
) -> dict[str, object]:
    """返回官方默认地址和已确认模型，页面不必手填容易出错的 URL。"""
    return {
        "embedding": [
            {"adapter_type": "dashscope", "name": "阿里云百炼", "model": "text-embedding-v4",
             "base_url": "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"},
            {"adapter_type": "siliconflow", "name": "SiliconFlow", "model": "BAAI/bge-m3",
             "base_url": "https://api.siliconflow.cn/v1"},
        ],
        "translation": [
            {"adapter_type": "siliconflow", "name": "SiliconFlow",
             "model": "Qwen/Qwen2.5-7B-Instruct", "base_url": "https://api.siliconflow.cn/v1"},
            {"adapter_type": "zhipu", "name": "智谱 AI", "model": "glm-4-flash",
             "base_url": "https://open.bigmodel.cn/api/paas/v4"},
        ],
    }


@router.post("/test", response_model=ConnectivityTestResponse)
async def test_model_provider_connectivity(
    payload: ConnectivityTestPayload,
    _account_manager: Annotated[object, Depends(require_account_manager)],
) -> ConnectivityTestResponse:
    """用最小请求探测地址、鉴权和模型能力，不落库、不写日志、不保存 API Key。"""
    try:
        if payload.purpose == "embedding":
            embedding_client = DashScopeEmbeddingClient(
                api_key=payload.api_key,
                base_url=payload.base_url,
                model=payload.model,
                dimension=1024,
            )
            await embedding_client.embed(["连接测试"])
        else:
            translation_client = OpenAICompatibleTranslationClient(
                api_key=payload.api_key,
                base_url=payload.base_url,
                model=payload.model,
            )
            await translation_client.translate(["Привет"])
    except CloudModelQuotaError:
        return ConnectivityTestResponse(
            ok=False,
            status="quota_exceeded",
            message="模型地址可达，但额度或限流已触发。",
            model=payload.model,
        )
    except (CloudModelError, ValueError) as error:
        return ConnectivityTestResponse(
            ok=False, status="failed", message=str(error), model=payload.model
        )
    return ConnectivityTestResponse(
        ok=True, status="reachable", message="模型连接成功，最小请求已完成。", model=payload.model
    )


def _response(item: dict[str, object]) -> ManagedProviderResponse:
    suffix = str(item.get("credential_suffix") or "")
    return ManagedProviderResponse(
        provider_id=str(item["id"]), name=str(item["name"]),
        adapter_type=str(item["adapter_type"]),
        model=str(item["model"]), base_url=str(item["base_url"]),
        model_kind=cast(ManagedModelKind, str(item.get("model_kind") or "text")),
        priority=int(cast(str | int, item["priority"])), enabled=bool(item["enabled"]),
        credential_configured=bool(item.get("credential_ref")),
        credential_mask=f"***{suffix}" if suffix else "",
    )


@router.get("", response_model=list[ManagedProviderResponse])
async def list_managed_model_providers(
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresRagModelProviderGateway, Depends(get_rag_model_provider_gateway)],
) -> list[ManagedProviderResponse]:
    return [_response(item) for item in await gateway.list_provider_metadata()]


@router.post("", response_model=ManagedProviderResponse, status_code=201)
async def create_managed_model_provider(
    payload: ManagedProviderPayload,
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresRagModelProviderGateway, Depends(get_rag_model_provider_gateway)],
    credentials: Annotated[ModelCredentialStore, Depends(get_model_credential_store)],
) -> ManagedProviderResponse:
    if not payload.api_key:
        raise HTTPException(status_code=422, detail="首次配置供应商必须提交 API Key")
    provider_id = str(uuid4())
    credential_ref = await credentials.put(provider_id, payload.api_key)
    await gateway.create_provider(
        provider_id=provider_id, name=payload.name, adapter_type=payload.adapter_type,
        model=payload.model, base_url=payload.base_url.rstrip("/"),
        model_kind=payload.model_kind,
        credential_ref=credential_ref, credential_suffix=payload.api_key.strip()[-4:],
        priority=payload.priority,
    )
    return _response({
        "id": provider_id, "name": payload.name, "adapter_type": payload.adapter_type,
        "model": payload.model, "base_url": payload.base_url.rstrip("/"),
        "model_kind": payload.model_kind,
        "priority": payload.priority, "enabled": True,
        "credential_ref": credential_ref, "credential_suffix": payload.api_key.strip()[-4:],
    })


@router.put("/{provider_id}", response_model=ManagedProviderResponse)
async def update_managed_model_provider(
    provider_id: str,
    payload: ManagedProviderPayload,
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresRagModelProviderGateway, Depends(get_rag_model_provider_gateway)],
    credentials: Annotated[ModelCredentialStore, Depends(get_model_credential_store)],
) -> ManagedProviderResponse:
    credential_ref = None
    suffix = None
    if payload.api_key:
        credential_ref = await credentials.put(provider_id, payload.api_key)
        suffix = payload.api_key.strip()[-4:]
    try:
        await gateway.update_provider(
            provider_id=provider_id, name=payload.name, adapter_type=payload.adapter_type,
            model=payload.model, base_url=payload.base_url.rstrip("/"),
            model_kind=payload.model_kind,
            priority=payload.priority, enabled=payload.enabled,
            credential_ref=credential_ref, credential_suffix=suffix,
        )
    except ValueError as error:
        if str(error) == "provider_bound_kind":
            raise HTTPException(
                status_code=409, detail="已绑定用途的模型不能直接切换模型类型，请先重新生成用途路由"
            ) from error
        raise
    item = next(
        (entry for entry in await gateway.list_provider_metadata()
         if str(entry["id"]) == provider_id), None
    )
    if item is None:
        raise HTTPException(status_code=404, detail="模型供应商不存在")
    return _response(item)


@router.delete("/{provider_id}", status_code=204)
async def delete_managed_model_provider(
    provider_id: str,
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresRagModelProviderGateway, Depends(get_rag_model_provider_gateway)],
) -> None:
    """删除未被用途绑定的配置，避免自动降级链出现悬挂引用。"""
    try:
        deleted = await gateway.delete_provider(provider_id)
    except ValueError as error:
        if str(error) == "provider_bound":
            raise HTTPException(
                status_code=409, detail="模型仍被用途绑定，请先停用或解绑"
            ) from error
        raise
    if not deleted:
        raise HTTPException(status_code=404, detail="模型供应商不存在")


@router.put("/bindings/{purpose}", response_model=ManagedBindingResponse)
async def bind_managed_model_purpose(
    purpose: ManagedPurpose,
    payload: ManagedBindingPayload,
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresRagModelProviderGateway, Depends(get_rag_model_provider_gateway)],
) -> ManagedBindingResponse:
    try:
        await gateway.bind_purpose(
            purpose=purpose,
            primary_provider_id=payload.primary_provider_id,
            fallback_provider_ids=payload.fallback_provider_ids,
        )
    except ValueError as error:
        error_messages = {
            "provider_duplicate": "主模型和备用模型不能重复",
            "provider_not_found": "模型供应商不存在或不属于当前工作区",
            "provider_disabled": "已停用的模型不能加入自动降级链",
            "provider_kind_mismatch": "向量用途只能绑定向量模型，文本用途只能绑定文本模型",
        }
        raise HTTPException(
            status_code=400,
            detail=error_messages.get(str(error), "模型用途绑定参数无效"),
        ) from error
    item = next(
        entry for entry in await gateway.list_bindings() if str(entry["purpose"]) == purpose
    )
    fallback_ids = cast(list[object], item["fallback_provider_ids"])
    return ManagedBindingResponse(
        purpose=purpose, primary_provider_id=str(item["primary_provider_id"]),
        fallback_provider_ids=[str(value) for value in fallback_ids],
        revision=int(cast(str | int, item["revision"])),
    )


@router.get("/bindings", response_model=list[ManagedBindingResponse])
async def list_managed_model_bindings(
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresRagModelProviderGateway, Depends(get_rag_model_provider_gateway)],
) -> list[ManagedBindingResponse]:
    return [ManagedBindingResponse(
        purpose=cast(ManagedPurpose, str(item["purpose"])),
        primary_provider_id=str(item["primary_provider_id"]),
        fallback_provider_ids=[
            str(value) for value in cast(list[object], item["fallback_provider_ids"])
        ],
        revision=int(cast(str | int, item["revision"])),
    ) for item in await gateway.list_bindings()]


@router.post("/{provider_id}/disable", response_model=ManagedProviderResponse)
async def disable_managed_model_provider(
    provider_id: str,
    _account_manager: Annotated[object, Depends(require_account_manager)],
    gateway: Annotated[PostgresRagModelProviderGateway, Depends(get_rag_model_provider_gateway)],
) -> ManagedProviderResponse:
    await gateway.disable_provider(provider_id)
    item = next(
        (entry for entry in await gateway.list_provider_metadata()
         if str(entry["id"]) == provider_id), None
    )
    if item is None:
        raise HTTPException(status_code=404, detail="模型供应商不存在")
    return _response(item)
