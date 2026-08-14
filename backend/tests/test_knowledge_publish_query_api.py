"""摄取、发布、问答和撤回的最小运行时闭环测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.knowledge_answers import router as answers_router
from backend.app.api.routes.knowledge_ingestion import router as ingestion_router
from backend.app.api.routes.knowledge_sources import router as sources_router


def test_ingested_version_is_queryable_only_after_publish() -> None:
    app = FastAPI()
    app.include_router(answers_router)
    app.include_router(ingestion_router)
    app.include_router(sources_router)
    client = TestClient(app)

    source = client.post(
        "/v1/knowledge-sources",
        json={
            "title": "库存 SOP",
            "source_type": "markdown",
            "business_domain": "sop",
            "source_locator": "docs/stock.md",
        },
    ).json()
    version = client.post(
        f"/v1/knowledge-sources/{source['id']}/versions",
        json={
            "content_hash": "hash-runtime",
            "parser_name": "markdown",
            "parser_version": "1",
            "cleaner_version": "1",
        },
    ).json()
    ingested = client.post(
        "/v1/knowledge-ingestion/run",
        json={
            "document_id": source["id"],
            "document_version_id": version["id"],
            "source_type": "markdown",
            "business_domain": "sop",
            "filename": "stock.md",
            "content": "# 库存 SOP\n\n库存安全线是 10 件。",
            "strategy": "markdown_sections",
            "source_locator": "docs/stock.md",
        },
    )
    assert ingested.status_code == 200
    assert ingested.json()["quality_passed"] is True

    published = client.post(f"/v1/knowledge-sources/versions/{version['id']}/publish")
    assert published.status_code == 200
    answer = client.post(
        "/v1/knowledge-answers/query", json={"question": "如何查看库存安全线"}
    ).json()
    assert answer["status"] == "answered"
    assert answer["segments"][0]["citations"][0]["source_locator"] == "docs/stock.md"

    withdrawn = client.post(f"/v1/knowledge-sources/versions/{version['id']}/withdraw")
    assert withdrawn.status_code == 200
    after_withdraw = client.post(
        "/v1/knowledge-answers/query", json={"question": "如何查看库存安全线"}
    ).json()
    assert after_withdraw["segments"][0]["citations"][0]["source_locator"] != "docs/stock.md"
