from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class ModelAdapterConfig:
    adapter: str
    provider: str
    model: str
    base_url: str | None
    enabled: bool
    credential_configured: bool


class ModelAdapterGateway(Protocol):
    async def save_config(
        self, *, workspace_id: str, config: ModelAdapterConfig
    ) -> ModelAdapterConfig: ...

    async def list_configs(
        self, *, workspace_id: str, limit: int
    ) -> list[ModelAdapterConfig]: ...

    async def get_active_config(
        self, *, workspace_id: str
    ) -> ModelAdapterConfig | None: ...


def inspect_model_adapter(
    *, adapter: str, provider: str, model: str, base_url: str | None,
    enabled: bool, credential_configured: bool,
) -> ModelAdapterConfig:
    """只检查厂商无关的适配器配置，不接触访问令牌，也不发起模型请求。"""
    normalized_adapter = adapter.strip().lower()
    if not normalized_adapter or not provider.strip() or not model.strip():
        raise ValueError("模型适配器、厂商和模型名称不能为空")
    if enabled and not credential_configured:
        raise ValueError("启用模型适配器前必须配置后端凭据")
    if base_url:
        parsed = urlparse(base_url.strip())
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("模型适配器地址必须是有效的 HTTP(S) 地址")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("非本地模型服务必须使用 HTTPS")
    return ModelAdapterConfig(
        adapter=normalized_adapter, provider=provider.strip(), model=model.strip(),
        base_url=base_url.strip() if base_url else None,
        enabled=enabled, credential_configured=credential_configured,
    )
