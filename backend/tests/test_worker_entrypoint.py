from pathlib import Path


def test_worker_entrypoint_delegates_to_sync_runtime() -> None:
    """部署入口必须存在，且把运行职责委托给统一同步运行时。"""

    source = Path("backend/app/worker.py").read_text(encoding="utf-8")

    assert "from backend.app.sync_runtime import worker_main" in source
    assert "worker_main()" in source
