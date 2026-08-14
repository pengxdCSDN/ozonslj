from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.knowledge_strategies import router


def test_strategy_registry_is_server_controlled() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/v1/knowledge-chunk-strategies?source_type=pdf")
    assert response.status_code == 200
    assert {item["name"] for item in response.json()} == {
        "pdf_pages", "pdf_paragraphs", "pdf_layout_blocks"
    }
