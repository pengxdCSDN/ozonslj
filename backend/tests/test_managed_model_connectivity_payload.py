"""模型供应商连通性测试请求的密钥回读边界。"""

import pytest

from backend.app.api.routes.managed_model_providers import (
    ConnectivityTestPayload,
    _validate_connectivity_target,
)


def test_existing_provider_connectivity_can_omit_api_key() -> None:
    """编辑已有配置时只提交供应商 ID，由服务端读取受保护凭据。"""
    payload = ConnectivityTestPayload(
        purpose="embedding",
        adapter_type="siliconflow",
        model="BAAI/bge-m3",
        base_url="https://api.siliconflow.cn/v1",
        provider_id="12345678-1234-1234-1234-123456789012",
    )
    assert payload.api_key is None
    assert payload.provider_id is not None


def test_new_provider_connectivity_accepts_transient_api_key() -> None:
    """新增配置仍可用请求内密钥测试，且该字段不参与响应模型。"""
    payload = ConnectivityTestPayload(
        purpose="translation",
        adapter_type="openai-compatible",
        model="Qwen/Qwen2.5-7B-Instruct",
        base_url="https://api.siliconflow.cn/v1",
        api_key="transient-test-key",
    )
    assert payload.api_key == "transient-test-key"
    assert payload.provider_id is None


@pytest.mark.parametrize("api_key", ["test", "test-key", "your-api-key", "changeme"])
def test_connectivity_rejects_placeholder_api_key(api_key: str) -> None:
    """占位密钥不能触发真实连接测试，避免未认证接口返回 200 造成假成功。"""
    with pytest.raises(ValueError, match="真实 API Key"):
        _validate_connectivity_target("openai-compatible", "https://api.vendor.example/v1", api_key)


def test_connectivity_rejects_example_target() -> None:
    """示例域名不能作为供应商连接测试目标。"""
    with pytest.raises(ValueError, match="真实模型供应商地址"):
        _validate_connectivity_target("openai-compatible", "https://example.com/v1", "real-key")


def test_builtin_adapter_requires_official_domain() -> None:
    """内置供应商适配器不能把密钥发往伪装的第三方域名。"""
    with pytest.raises(ValueError, match="官方模型接口地址"):
        _validate_connectivity_target("siliconflow", "https://api.attacker.invalid/v1", "real-key")
