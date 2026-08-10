"""生产 Worker 进程入口。

部署镜像通过 ``python -m backend.app.worker`` 启动 Worker；实际组装逻辑
集中在 ``sync_runtime``，保证 API、Scheduler 和 Worker 共用同一套配置与
PostgreSQL/Redis 适配边界。
"""

from backend.app.sync_runtime import worker_main

if __name__ == "__main__":
    worker_main()
