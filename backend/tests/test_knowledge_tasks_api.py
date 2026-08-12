from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.knowledge_tasks import router


def test_task_is_idempotent_claimed_and_finished() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    created = client.post(
        "/v1/knowledge-tasks", json={"task_type": "index", "organization_id": "org-1"}
    )
    task_id = created.json()["task_id"]
    listed = client.get("/v1/knowledge-tasks?organization_id=org-1")
    assert listed.status_code == 200
    assert listed.json()[0]["task_id"] == task_id
    claimed = client.post(f"/v1/knowledge-tasks/{task_id}/claim?organization_id=org-1")
    assert claimed.json()["status"] == "running"
    finished = client.post(
        f"/v1/knowledge-tasks/{task_id}/finish", json={"status": "succeeded"}
    )
    assert finished.json()["status"] == "succeeded"
