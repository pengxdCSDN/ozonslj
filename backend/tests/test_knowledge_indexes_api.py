from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.knowledge_indexes import router


def test_index_reconcile_blocks_missing_metadata_and_removes_orphans() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/v1/knowledge-indexes/reconcile",
        json={
            "published_chunk_ids": ["a", "b"], "indexed_chunk_ids": ["b", "c"],
            "metadata_chunk_ids": ["a"],
        },
    )
    body = response.json()
    assert body["upsert_ids"] == ["a"]
    assert body["delete_ids"] == ["c"]
    assert body["safe_to_publish"] is False
