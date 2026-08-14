from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.knowledge_ingestion import router


def test_ingestion_api_runs_parser_cleaner_chunker_and_gate() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/v1/knowledge-ingestion/run",
        json={
            "source_type": "markdown", "business_domain": "sop", "filename": "sop.md",
            "content": "# 同步\n\n失败后检查任务状态。", "strategy": "markdown_sections",
            "source_locator": "docs/sop.md",
        },
    )
    assert response.status_code == 200
    assert response.json()["quality_passed"] is True
    assert response.json()["chunks"]


def test_ingestion_api_returns_validation_error_for_unknown_strategy() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/v1/knowledge-ingestion/run",
        json={
            "source_type": "markdown", "business_domain": "sop", "filename": "sop.md",
            "content": "# 标题\n\n正文", "strategy": "not-registered",
            "source_locator": "docs/sop.md",
        },
    )
    assert response.status_code == 422
