"""模型供应商连通性测试请求的密钥回读边界。"""

from backend.app.api.routes.managed_model_providers import ConnectivityTestPayload


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
