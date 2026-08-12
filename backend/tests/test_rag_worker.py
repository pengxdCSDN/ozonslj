"""RAG Worker 租约和幂等任务测试。"""

from datetime import UTC, datetime

import pytest

from backend.app.domain.rag_worker import RagWorkerQueue, RagWorkerTask


def test_queue_claim_finish_and_idempotency() -> None:
    queue = RagWorkerQueue(max_concurrency=1, lease_seconds=60)
    task = RagWorkerTask("t1", "index", "org-1")
    assert queue.enqueue(task) == queue.enqueue(task)
    claimed = queue.claim(organization_id="org-1", now=datetime.now(UTC))
    assert claimed is not None
    assert queue.claim(organization_id="org-1") is None
    finished = queue.finish("t1", status="succeeded")
    assert finished.status == "succeeded"


def test_only_running_task_can_finish() -> None:
    queue = RagWorkerQueue()
    queue.enqueue(RagWorkerTask("t2", "delete", "org-1"))
    with pytest.raises(ValueError, match="running"):
        queue.finish("t2", status="failed", error_code="x")


def test_queue_lists_by_organization() -> None:
    queue = RagWorkerQueue(max_concurrency=1, lease_seconds=10)
    queue.enqueue(RagWorkerTask("a", "index", "org-a"))
    queue.enqueue(RagWorkerTask("b", "index", "org-b"))
    assert [task.task_id for task in queue.list(organization_id="org-a")] == ["a"]
