"""知识源新增、查询和撤回接口回归测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.knowledge_sources import router


def test_source_lifecycle() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    created = client.post(
        "/v1/knowledge-sources",
        json={
            "title": "运营 SOP", "source_type": "markdown", "business_domain": "sop",
            "source_locator": "docs/sop.md",
        },
    )
    assert created.status_code == 201
    source_id = created.json()["id"]
    assert client.get("/v1/knowledge-sources").json()[0]["status"] == "active"
    withdrawn = client.post(f"/v1/knowledge-sources/{source_id}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"


def test_version_publish_replaces_previous_published_version() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    created = client.post(
        "/v1/knowledge-sources",
        json={
            "title": "字段说明", "source_type": "markdown", "business_domain": "database",
            "source_locator": "docs/database.md",
        },
    )
    source_id = created.json()["id"]
    payload = {
        "content_hash": "hash-v1", "parser_name": "markdown", "parser_version": "1",
        "cleaner_version": "1",
    }
    first = client.post(f"/v1/knowledge-sources/{source_id}/versions", json=payload).json()
    first_published = client.post(
        f"/v1/knowledge-sources/versions/{first['id']}/publish"
    )
    assert first_published.json()["status"] == "published"
    second = client.post(
        f"/v1/knowledge-sources/{source_id}/versions",
        json={**payload, "content_hash": "hash-v2"},
    ).json()
    second_published = client.post(
        f"/v1/knowledge-sources/versions/{second['id']}/publish"
    )
    assert second_published.json()["status"] == "published"
    versions = client.get(f"/v1/knowledge-sources/{source_id}/versions").json()
    assert [version["status"] for version in versions] == ["withdrawn", "published"]


def test_source_pause_resume_delete_lifecycle() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    created = client.post(
        "/v1/knowledge-sources",
        json={
            "title": "生命周期", "source_type": "markdown", "business_domain": "general",
            "source_locator": "docs/lifecycle.md",
        },
    )
    source_id = created.json()["id"]
    assert client.post(f"/v1/knowledge-sources/{source_id}/pause").json()["status"] == "paused"
    assert client.post(f"/v1/knowledge-sources/{source_id}/resume").json()["status"] == "active"
    assert client.delete(f"/v1/knowledge-sources/{source_id}").json()["status"] == "deleted"
