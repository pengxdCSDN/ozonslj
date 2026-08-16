# 可观测性与运维（P3-10）

## 已实现范围

- API 请求总量、状态码和耗时：进程内聚合并通过 `/metrics` 输出 Prometheus 文本格式。
- 模型调用总量、错误量和耗时：按受控的模型用途、供应商和错误状态聚合；不保存提示词、响应正文或 API Key。
- Scheduler 投递周期/数量、Seller 与 RAG Worker 已处理任务数量。
- `/health/live`、`/health/ready`、`/health/rag` 和 `/health/ops` 发布后检查端点。
- `/health/ops` 读取容器可见内存、Swap、磁盘使用率；磁盘达到 85% 返回 `warning`，不影响登录和只读页面。
- `deploy/scripts/post_release_gate.sh` 执行 Compose 配置校验、健康检查、指标出口检查；默认失败保留现场，只有显式设置 `ROLLBACK_ON_FAILURE=1` 和上一版镜像标签才回滚 API/Worker/Scheduler 并刷新 Web。
- 现有 PostgreSQL 审计事件和归档策略继续承担业务审计；请求日志/指标不记录 Cookie、查询参数、请求体、令牌或客户正文。

## 云端验收

在 `/opt/ozonslj/app/deploy` 执行：

```bash
bash scripts/post_release_gate.sh
```

门禁通过必须同时满足：Compose 配置有效、`live=200`、`ready=200`、`ops=200`、指标中存在请求计数和资源指标。出现 5xx、健康检查失败、磁盘告警或静态资源 MIME 错误时，发布判定失败；回滚必须使用已核对过的上一版应用标签，不能回滚 PostgreSQL 数据或基础设施容器。

## 限制与后续

指标首期是单进程内存聚合，重启后计数归零；当前部署规模为单 API/Worker/Scheduler 副本，满足内部运维验收。扩容前必须引入外部 Prometheus/日志归档并为实例增加 `instance` 标签，不能直接把用户输入写入标签。

## 2026-08-16 云端最终验收

ACR 应用摘要 `sha256:e2cde1e36edbf00876f6bba367f40cf2bc5534694ca9e40e46f6915b68d5367b` 已部署到 API、Worker、Scheduler。`live/ready/ops` 均为 200，`/metrics` 返回请求与资源指标，磁盘约 45.15%，Nginx 配置和 HTTPS 首页通过。
