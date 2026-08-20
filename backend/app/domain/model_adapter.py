"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class ModelAdapterConfig:
    """说明 ModelAdapterConfig 的职责、状态边界和对外协作关系。"""
    adapter: str
    provider: str
    model: str
    base_url: str | None
    enabled: bool
    credential_configured: bool


class ModelAdapterGateway(Protocol):
    """说明 ModelAdapterGateway 的职责、状态边界和对外协作关系。"""
    async def save_config(
        self, *, workspace_id: str, config: ModelAdapterConfig
    ) -> ModelAdapterConfig:
        """执行 save_config 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    config: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_configs(
        self, *, workspace_id: str, limit: int
    ) -> list[ModelAdapterConfig]:
        """执行 list_configs 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def get_active_config(
        self, *, workspace_id: str
    ) -> ModelAdapterConfig | None:
        """执行 get_active_config 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def inspect_model_adapter(
    *, adapter: str, provider: str, model: str, base_url: str | None,
    enabled: bool, credential_configured: bool,
) -> ModelAdapterConfig:
    """只检查厂商无关的适配器配置，不接触访问令牌，也不发起模型请求。

Args:
    adapter: 参数语义、输入边界和安全约束。
    provider: 参数语义、输入边界和安全约束。
    model: 参数语义、输入边界和安全约束。
    base_url: 参数语义、输入边界和安全约束。
    enabled: 参数语义、输入边界和安全约束。
    credential_configured: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
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
