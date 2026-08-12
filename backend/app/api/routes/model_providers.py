"""模型供应商配置和用途主备绑定 API。"""

from __future__ import annotations

from typing import cast
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/model-providers", tags=["model-providers"])
_providers: dict[str, dict[str, object]] = {}
_bindings: dict[str, dict[str, object]] = {}


class ProviderCreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    adapter_type: str = Field(pattern="^(deepseek|minimax|openai|openai_compatible)$")
    model: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500)
    priority: int = Field(default=100, ge=1, le=1000)


class ProviderResponse(BaseModel):
    provider_id: str
    name: str
    adapter_type: str
    model: str
    priority: int
    enabled: bool
    credential_configured: bool
    credential_mask: str


class BindingPayload(BaseModel):
    primary_provider_id: str
    fallback_provider_ids: list[str] = Field(default_factory=list, max_length=3)


def _response(provider_id: str, item: dict[str, object]) -> ProviderResponse:
    api_key = str(item["api_key"])
    return ProviderResponse(
        provider_id=provider_id, name=str(item["name"]), adapter_type=str(item["adapter_type"]),
        model=str(item["model"]),
        priority=cast(int, item["priority"]), enabled=bool(item["enabled"]),
        credential_configured=bool(api_key),
        credential_mask=f"***{api_key[-4:]}" if api_key else "",
    )


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_model_provider(payload: ProviderCreatePayload) -> ProviderResponse:
    provider_id = str(uuid4())
    _providers[provider_id] = {**payload.model_dump(), "enabled": True}
    return _response(provider_id, _providers[provider_id])


@router.get("", response_model=list[ProviderResponse])
async def list_model_providers() -> list[ProviderResponse]:
    return [_response(provider_id, item) for provider_id, item in _providers.items()]


@router.post("/{provider_id}/disable", response_model=ProviderResponse)
async def disable_model_provider(provider_id: str) -> ProviderResponse:
    item = _providers.get(provider_id)
    if item is None:
        raise HTTPException(status_code=404, detail="模型供应商不存在")
    item["enabled"] = False
    return _response(provider_id, item)


@router.put("/bindings/{purpose}", response_model=dict[str, object])
async def bind_model_purpose(purpose: str, payload: BindingPayload) -> dict[str, object]:
    provider_ids = [payload.primary_provider_id, *payload.fallback_provider_ids]
    if len(set(provider_ids)) != len(provider_ids):
        raise HTTPException(status_code=400, detail="主备供应商不能重复")
    if any(provider_id not in _providers for provider_id in provider_ids):
        raise HTTPException(status_code=404, detail="绑定的模型供应商不存在")
    _bindings[purpose] = {
        "primary_provider_id": provider_ids[0], "fallback_provider_ids": provider_ids[1:]
    }
    return {"purpose": purpose, **_bindings[purpose]}
