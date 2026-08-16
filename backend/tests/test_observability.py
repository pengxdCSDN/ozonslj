from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_readiness_probe
from backend.app.infrastructure.observability import METRICS, MetricsRegistry
from backend.app.main import app


class ReadyProbe:
    async def check(self) -> None:
        return None


def test_metrics_registry_renders_aggregates_without_high_cardinality_labels() -> None:
    registry = MetricsRegistry()
    registry.inc("example_total", labels={"status": "ok"})
    registry.observe("example_duration_seconds", 0.1, labels={"route": "/health/*"})

    rendered = registry.render()

    assert 'example_total{status="ok"} 1' in rendered
    assert 'example_duration_seconds_bucket{le="0.1",route="/health/*"} 1' in rendered
    assert 'example_duration_seconds_count{route="/health/*"} 1' in rendered


def test_metrics_endpoint_exposes_request_and_resource_aggregates(monkeypatch) -> None:
    monkeypatch.delenv("CHROMA_URL", raising=False)
    app.dependency_overrides[get_readiness_probe] = lambda: ReadyProbe()
    try:
        client = TestClient(app)
        assert client.get("/health/live").status_code == 200
        response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "ozonslj_http_requests_total" in response.text
    assert (
        "ozonslj_memory_available_bytes" in response.text
        or "ozonslj_disk_used_ratio" in response.text
    )
    # 测试共享的全局注册表仅用于进程聚合，不得把请求参数作为标签。
    assert "secret" not in METRICS.render().lower()


def test_operations_health_is_non_blocking_when_resource_probe_is_partial(monkeypatch) -> None:
    monkeypatch.delenv("CHROMA_URL", raising=False)
    response = TestClient(app).get("/health/ops")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "warning"}
