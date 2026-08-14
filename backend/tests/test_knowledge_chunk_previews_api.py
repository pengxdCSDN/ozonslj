"""切片策略入口和质量报告 API 测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.knowledge_chunk_previews import router


def test_markdown_preview_returns_metadata_and_quality() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/v1/knowledge-chunk-previews",
        json={
            "source_type": "markdown", "business_domain": "sop",
            "strategy": "markdown_sections", "content": "# 库存\n\n同步失败时检查任务状态。",
            "source_locator": "docs/sop.md",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunks"][0]["title_path"] == ["库存"]
    assert body["quality"]["passed"] is True
