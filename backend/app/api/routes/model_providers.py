"""兼容旧版模型供应商配置 API。

真实 RAG 配置使用 ``managed_model_providers`` 路由；本模块保留旧版 Stub
接口以兼容既有开发测试，不用于生产凭据存储。
"""

from __future__ import annotations

from typing import cast
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/model-providers", tags=["model-providers"])
_providers: dict[str, dict[str, object]] = {}
_bindings: dict[str, dict[str, object]] = {}


class ProviderCreatePayload(BaseModel):
    """说明 ProviderCreatePayload 的职责、状态边界和对外协作关系。"""
    name: str = Field(min_length=1, max_length=80)
    adapter_type: str = Field(pattern="^(dashscope|deepseek|minimax|openai|openai_compatible)$")
    model: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500, repr=False)
    base_url: str | None = Field(default=None, max_length=500)
    priority: int = Field(default=100, ge=1, le=1000)


class ProviderResponse(BaseModel):
    """说明 ProviderResponse 的职责、状态边界和对外协作关系。"""
    provider_id: str
    name: str
    adapter_type: str
    model: str
    base_url: str | None
    priority: int
    enabled: bool
    credential_configured: bool
    credential_mask: str


class BindingPayload(BaseModel):
    """说明 BindingPayload 的职责、状态边界和对外协作关系。"""
    primary_provider_id: str
    fallback_provider_ids: list[str] = Field(default_factory=list, max_length=3)


def _response(provider_id: str, item: dict[str, object]) -> ProviderResponse:
    """执行内部步骤 _response，供同一模块的公开流程复用。

Args:
    provider_id: 参数语义、输入边界和安全约束。
    item: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    api_key = str(item["api_key"])
    return ProviderResponse(
        provider_id=provider_id,
        name=str(item["name"]),
        adapter_type=str(item["adapter_type"]),
        model=str(item["model"]),
        base_url=str(item["base_url"]) if item.get("base_url") else None,
        priority=cast(int, item["priority"]),
        enabled=bool(item["enabled"]),
        credential_configured=bool(api_key),
        credential_mask=f"***{api_key[-4:]}" if api_key else "",
    )


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_model_provider(payload: ProviderCreatePayload) -> ProviderResponse:
    """执行 create_model_provider 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    provider_id = str(uuid4())
    _providers[provider_id] = {**payload.model_dump(), "enabled": True}
    return _response(provider_id, _providers[provider_id])


@router.get("", response_model=list[ProviderResponse])
async def list_model_providers() -> list[ProviderResponse]:
    """执行 list_model_providers 的业务流程并返回该流程的结果。
Returns:
    返回调用完成后的领域结果。"""
    return [_response(provider_id, item) for provider_id, item in _providers.items()]


@router.post("/{provider_id}/disable", response_model=ProviderResponse)
async def disable_model_provider(provider_id: str) -> ProviderResponse:
    """执行 disable_model_provider 的业务流程并返回该流程的结果。

Args:
    provider_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    item = _providers.get(provider_id)
    if item is None:
        raise HTTPException(status_code=404, detail="模型供应商不存在")
    item["enabled"] = False
    return _response(provider_id, item)


@router.put("/bindings/{purpose}", response_model=dict[str, object])
async def bind_model_purpose(purpose: str, payload: BindingPayload) -> dict[str, object]:
    """执行 bind_model_purpose 的业务流程并返回该流程的结果。

Args:
    purpose: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    provider_ids = [payload.primary_provider_id, *payload.fallback_provider_ids]
    if len(set(provider_ids)) != len(provider_ids):
        raise HTTPException(status_code=400, detail="主备供应商不能重复")
    if any(provider_id not in _providers for provider_id in provider_ids):
        raise HTTPException(status_code=404, detail="绑定的模型供应商不存在")
    _bindings[purpose] = {
        "primary_provider_id": provider_ids[0],
        "fallback_provider_ids": provider_ids[1:],
    }
    return {"purpose": purpose, **_bindings[purpose]}
