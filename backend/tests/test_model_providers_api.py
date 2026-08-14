"""模型供应商配置接口的凭据不回显测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.model_providers import router


def test_provider_config_and_binding() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    created = client.post(
        "/v1/model-providers",
        json={
            "name": "DeepSeek", "adapter_type": "deepseek", "model": "chat",
            "api_key": "secret-value",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert "secret-value" not in created.text
    provider_id = body["provider_id"]
    binding = client.put(
        "/v1/model-providers/bindings/answer_generation",
        json={"primary_provider_id": provider_id},
    )
    assert binding.status_code == 200
