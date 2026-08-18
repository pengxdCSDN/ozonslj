# ozonslj HTTP API 契约

> 本文是前后端 HTTP 契约的持续维护入口，文档职责见 [项目文档索引](./README.md)。接口必须标明“已实现”或“已定档待开发”；内部路径不代表 Ozon 上游路径已核验。

知识型混合 RAG 的需求与架构已经定档，核心 HTTP 路由已实现并通过契约测试；目标契约仍集中维护在 [RAG HTTP API 目标契约](./RAG_API_TARGET.md)，本文记录已接入主应用的稳定接口。

## 1. 通用约定

- 业务前缀统一为 `/v1`，沿用已实现接口，不新增并行 `/api/v1`。
- 本地开发地址默认 `http://127.0.0.1:8000`；云端通过同源 HTTPS 和反向代理访问。
- JSON 使用 UTF-8；时间使用 UTC ISO 8601；金额在 API 中使用十进制字符串或明确的最小货币单位整数，不使用浮点数。
- 所有业务响应和错误携带 `X-Request-ID`；异步任务同时携带任务 ID。
- 凭据、密文、完整 Client ID、令牌、敏感请求头和未脱敏上游响应不得出现在响应。
- 列表使用稳定排序与游标分页；默认/最大页大小由资源契约明确，禁止无边界返回全量。
- 当前已实现接口已具备服务端请求状态到 PostgreSQL RLS 的上下文桥接，但尚未接入用户会话；缺少认证上下文时默认返回 `401`。云端开放前必须完成内建认证、组织成员和工作区授权，不能仅依赖路径中的 `workspace_id`，也不能信任客户端自报租户请求头。

统一业务错误：

```json
{
  "detail": {
    "code": "workspace_pending",
    "message": "工作区尚未验证",
    "request_id": "req_01...",
    "retryable": false
  }
}
```

错误不得泄露其他组织是否存在相同用户、Client ID、工作区或业务对象。

## 2. 认证与租户上下文（登录、会话、Redis 限流和 RLS 桥接已实现）

- Web 使用 HttpOnly Cookie 会话；状态变更请求执行 CSRF 校验。
- Chrome 扩展通过 Web 登录后生成的短时单次授权码换取扩展会话。
- API 从认证会话解析 `user_id`，从授权资源解析 `organization_id` 和 `workspace_id`；客户端不得通过任意请求头伪造租户上下文。
- 认证层必须把经过验证的 `TenantContext` 写入服务端 `request.state`；数据库依赖只接受该对象。直接发送 `X-Organization-Id` 或 `X-User-Id` 不会建立身份。
- 每个用例校验用户状态、组织成员状态、角色、工作区授权和工作区启用状态，并在同一 PostgreSQL 事务内设置 RLS 上下文。
- 创建卖家账户、替换凭据和验证凭据仅允许 `owner` 或 `admin`；运营主管、运营人员、财务和只读分析人员即使拥有工作区读取权限也不能管理凭据。
- 未认证返回 `401`；组织成员/工作区越权返回 `403`；不存在且允许暴露的资源返回 `404`。
- 验证/重置请求返回相同通用响应，避免邮箱枚举；原始令牌只进入 HTTPS 邮件链接和消费请求，不在任何读取接口返回。

目标认证资源：

| 方法 | 路径 | 用途 | 状态 |
|---|---|---|---|
| POST | `/v1/auth/login` | 使用邮箱、密码和组织 ID 创建 Web 会话；失败受 Redis 限流 | 已实现 |
| GET | `/v1/auth/me` | 返回当前用户、活动组织和组织角色 | 已实现 |
| POST | `/v1/auth/logout` | 撤销当前会话 | 已实现 |
| POST | `/v1/auth/email-verifications` | 创建验证邮件任务；不泄露邮箱状态 | 待开发 |
| POST | `/v1/auth/email-verifications/consume` | 单次消费邮箱验证令牌 | 待开发 |
| POST | `/v1/auth/password-resets` | 创建密码重置邮件任务；不泄露账户状态 | 待开发 |
| POST | `/v1/auth/password-resets/consume` | 单次消费重置令牌并撤销既有会话 | 待开发 |
| POST | `/v1/auth/extension-codes` | 生成扩展一次性授权码 | 待开发 |
| POST | `/v1/auth/extension-sessions` | 兑换扩展会话 | 待开发 |

## 3. 健康检查（已实现）

| 方法 | 路径 | 响应 |
|---|---|---|
| GET | `/health/live` | 只验证 API 进程可响应；不访问外部依赖 |
| GET | `/health/ready` | 并行执行 PostgreSQL `SELECT 1` 与 Redis `PING`；任一失败返回 `503 infrastructure_unavailable` |
| GET | `/health/live` | 进程存活，不依赖外部服务 |
| GET | `/health/ready` | 当前依赖是否可承接流量 |

生产就绪检查必须验证 PostgreSQL；Redis 不可用时若任务功能不可承接，应返回未就绪，但不得把 Redis 当作业务事实来源。

## 4. 店铺工作区与 Seller 凭据（已实现本地切片）

### 4.1 查询工作区

`GET /v1/store-workspaces`

返回脱敏工作区列表，不包含 Client ID、Api-Key、密文、密钥版本或上游响应。云端版本只返回当前用户获授权的组织/工作区。

### 4.2 创建工作区

`POST /v1/store-workspaces`

```json
{
  "display_name": "俄罗斯主店",
  "client_id": "仅在请求中传输",
  "api_key": "仅在请求中传输"
}
```

- 成功返回 `201` 和状态 `pending` 的脱敏工作区。
- 创建不隐式验证凭据；验证使用独立接口。
- Client ID 冲突只按当前组织判断，不泄露其他组织是否存在相同值。

### 4.3 替换凭据

`PUT /v1/store-workspaces/{workspace_id}/credentials`

成功后状态重置为 `pending`，清空验证时间，旧凭据不可继续使用。云端实现必须使用信封加密写入 PostgreSQL，不得使用机器绑定的本地密文方案。

### 4.4 验证凭据

`POST /v1/store-workspaces/{workspace_id}/verify`

| 结果 | HTTP | 错误代码 | 工作区状态 |
|---|---:|---|---|
| 成功 | 200 | 无 | `active` |
| 认证失败 | 401 | `authentication_failed` | `invalid` |
| 权限不足 | 403 | `permission_denied` | `invalid` |
| 限流 | 429 | `rate_limited` | 保持原状态 |
| 网络、超时、上游 5xx | 503 | `temporary_failure` | 保持原状态 |
| 响应畸形 | 503 | `malformed_response` | 保持原状态 |
| 密文不可用 | 422 | `credential_unavailable` | `invalid` |

自动化测试使用 HTTP Mock，不访问真实账户。实际 Seller 验证方法在实现/验收前核对官方文档，不在内部契约中固化未经验证的上游路径。

## 5. 商品报价（已实现本地切片）

`GET /v1/store-workspaces/{workspace_id}/product-offers`

查询参数：

| 参数 | 类型 | 默认 | 约束 |
|---|---|---:|---|
| `cursor` | string | 空 | 非负游标 |
| `limit` | integer | 20 | 1～100 |

响应：

```json
{
  "items": [
    {
      "offer_id": "CN-MUG-420-BL",
      "ozon_product_id": "1847295031",
      "name": "双层保温杯 420ml",
      "price": "1290.00",
      "currency": "RUB",
      "available_stock": 37
    }
  ],
  "total": 1,
  "next_cursor": null,
  "source": "postgres"
}
```

当前代码仍通过历史持久化适配器返回数据；PostgreSQL 适配器完成前，本接口只能标记为“业务切片已实现、数据库迁移未完成”。

## 6. Seller 同步与查询（当前已实现的只读/任务控制能力）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/v1/store-workspaces/{id}/sync-jobs` | 持久化创建商品/库存/订单/履约同步任务（已实现） |
| GET | `/v1/sync-jobs/{id}` | 查询任务状态（已实现） |
| GET | `/v1/store-workspaces/{id}/sync-jobs` | 查询工作区同步任务历史（已实现，数字游标） |
| POST | `/v1/sync-jobs/{id}/cancel` | 请求取消排队或执行中的任务（已实现） |
| POST | `/v1/sync-jobs/{id}/retry` | 对失败或部分成功任务重新排队（已实现） |
| GET | `/v1/store-workspaces/{id}/stock-positions` | 查询已同步的 FBO/FBS 库存位置（已实现） |
| GET | `/v1/store-workspaces/{id}/customer-orders` | 查询脱敏订单摘要（已实现） |
| GET | `/v1/store-workspaces/{id}/postings` | 查询 FBO/FBS 履约摘要（已实现） |
| GET | `/v1/store-workspaces/{id}/seller-operations` | 查询脱敏审计时间线（已实现） |

同步任务历史使用 `cursor` 数字偏移游标和 `limit=1..100`；任务取消不会删除任务，
排队任务直接进入 `cancelled`，执行中任务记录取消请求；重试仅允许 `failed` 或
`partial` 任务重新进入 `queued`。

库存位置查询使用与商品列表相同的数字游标，`limit` 范围为 1～100。响应中的
`available_quantity` 与 `reserved_quantity` 分开表达，不能合并为一个含义不明的库存数；
`fulfillment_type` 仅允许 `FBO` 或 `FBS`。该接口只读取 PostgreSQL 已同步事实，不在请求线程
内访问 Ozon；未知工作区返回 `404`，待验证工作区返回 `409`，凭据无效或停用返回 `403`。

客户订单查询使用同样的数字游标和分页上限，按 `ordered_at` 倒序返回订单编号、状态、精确金额、币种、下单时间和同步时间。接口不选择或返回 `raw_summary`、买家身份、地址、电话等敏感字段，也不在请求线程访问 Ozon。

履约查询返回履约编号、关联订单、FBO/FBS、状态、计划发货日期、商品行数、总件数和同步时间。列表接口不选择或返回物流追踪号及商品明细；分页上限为 100，并按计划发货日期倒序稳定排序。

审计时间线按发生时间倒序返回操作类型、风险级别、目标类型与数量、请求编号和结果。接口采用固定字段白名单，不选择或返回 `detail`、用户内部标识、凭据或上游错误原文。

创建任务必须使用幂等键；相同工作区、资源、时间窗和输入指纹不得产生重复有效任务。Redis 消息丢失后，任务仍可从 PostgreSQL 恢复。

当前创建接口要求 `Idempotency-Key` 请求头，长度 8～120；请求体 `resource_type` 仅允许 `products`、`stock`、`orders`、`postings`。接口返回 `202`、`Location` 和 `Retry-After: 2`。本阶段只保证 PostgreSQL 中持久化为 `queued`，Redis 投递与 Worker 执行在后续任务闭环中实现。

## 7. 异步任务通用契约（已确认待开发）

创建同步、导入、采样、研究、报告或执行任务返回：

```http
HTTP/1.1 202 Accepted
Location: /v1/tasks/task_01...
Retry-After: 2
```

```json
{
  "id": "task_01...",
  "status": "queued",
  "status_url": "/v1/tasks/task_01..."
}
```

- 状态资源提供 `ETag`，客户端使用 `If-None-Match`；未变化返回 `304`。
- Web/扩展首期使用 HTTP 退避轮询，不使用 WebSocket/SSE，不直接读取 Redis。
- 状态包含阶段、已处理/总数（可得时）、最近心跳、尝试次数、下次重试、部分失败数、更新时间和脱敏错误。
- 未知总量不得伪造百分比。
- `succeeded`、`partial`、`failed`、`cancelled`、`expired`、`manual_review` 等终态停止轮询。

## 8. 搜索词导入与公开采样（已定档待开发）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/v1/store-workspaces/{id}/keyword-report-imports` | 上传 CSV/XLSX 并创建解析任务 |
| GET | `/v1/store-workspaces/{id}/keyword-report-imports` | 查询导入历史 |
| POST | `/v1/store-workspaces/{id}/competitor-seeds` | 创建受控竞品种子 |
| GET | `/v1/store-workspaces/{id}/competitor-seeds` | 查询种子与采样状态 |
| POST | `/v1/store-workspaces/{id}/competitor-seeds/{seed_id}/collect` | 手动触发单个种子采样 |
| GET | `/v1/store-workspaces/{id}/public-product-snapshots` | 查询公开字段快照 |

上传接口限制文件大小、类型、编码、解压后大小和行列数量，计算内容指纹并幂等。开发阶段文件加密暂存服务器私有目录 7 天；响应不返回服务器路径。

竞品种子不接受任意 URL 透传：服务端只接受允许的 HTTPS 域名和规范化商品 URL。被 robots、策略、登录、验证码或访问限制禁止时不发请求，并返回明确采样状态。

## 9. 选品、Listing 与广告（已定档待开发）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/v1/store-workspaces/{id}/research-runs` | 创建 Explore/Validate/Expand 研究 |
| GET | `/v1/store-workspaces/{id}/research-runs/{run_id}` | 查询研究状态和来源摘要 |
| GET | `/v1/store-workspaces/{id}/product-decisions/{id}` | 查询结构化决策书 |
| POST | `/v1/store-workspaces/{id}/listing-drafts` | 生成 Listing 草稿 |
| POST | `/v1/store-workspaces/{id}/listing-drafts/{id}/risk-checks` | 创建风险检测 |
| GET | `/v1/store-workspaces/{id}/ad-analytics` | 查询只读广告指标和建议 |

研究/分析响应必须包含来源、统计时间、样本范围、算法/假设版本、完整度和估算标识。Listing 风险检测返回发现与建议，不覆盖原始草稿。广告建议不自动写入 Performance API。

## 10. 审核与受控写入（V5.4，已定档待开发）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/v1/store-workspaces/{id}/review-requests` | 创建待审核请求 |
| GET | `/v1/store-workspaces/{id}/review-requests` | 查询审核队列 |
| POST | `/v1/review-requests/{id}/approve` | 人工批准并创建执行命令 |
| POST | `/v1/review-requests/{id}/reject` | 人工拒绝 |
| GET | `/v1/execution-commands/{id}` | 查询分项执行与回读结果 |

批准接口必须重新校验权限、审核状态、预览版本和数据新鲜度，并使用幂等键。API 只创建命令；独立 `execution-worker` 执行写入。首个价格写入每批最多 20 件、涨跌不超过 10%、不得低于利润线。结果不确定时返回 `verification_required` 或 `manual_review`，不得盲目重试。

## 11. RAG 评测案例确认（已实现）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/v1/rag-evaluation/case-generation-jobs` | 创建 AI 草稿案例 |
| GET | `/v1/rag-evaluation/cases?page=1&page_size=20&q=...` | 分页搜索当前组织的固定/草稿案例；`q` 匹配案例 ID、问题、状态和安全标签 |
| POST | `/v1/rag-evaluation/cases/{case_id}/confirm` | 单条人工确认 |
| POST | `/v1/rag-evaluation/cases/confirm-batch` | 批量人工确认，最多 240 个案例 |
| POST | `/v1/rag-evaluation/runs` | 创建评测运行并计算确认门禁 |
| GET | `/v1/rag-evaluation/runs?limit=20` | 查看当前组织的评测运行历史与脱敏指标；前端按批次分页展示，`run_id` 为内部追踪号，不要求用户填写 |
| GET | `/v1/rag-evaluation/runs/{run_id}` | 查看单次评测运行结果 |
| POST | `/v1/rag-evaluation/runs/{run_id}/metrics` | 由评测 Worker 回写单次运行的聚合指标 |

评测案例列表响应为 `{items, total, page, page_size, total_pages, draft_count, confirmed_count}`。历史 `fixed-rag-v1` 案例保留在 PostgreSQL 供审计，但列表只展示当前 `fixed-rag-v2`；Seller 店铺未验证不阻断 RAG 评测页面。

评测结果页读取运行历史中的 `status`、`executed_count`、错误数量和指标快照。指标快照只保存 Recall、Precision、引用支持率、正确拒答率、多意图、安全和主备降级等聚合结果，不保存问题正文、提示词、凭据或模型原始响应。`gate_status=ready` 仅表示案例确认门禁通过；只有运行完成并且指标达到 [RAG 质量运行手册](./RAG_QUALITY_RUNBOOK.md) 的硬门槛时，结果状态才显示为质量通过。

固定 400 例通过 PostgreSQL 幂等种子写入；确认状态、确认人和确认时间不保存在 API 进程内存中，API 重启后必须保持。未确认案例不能通过运行门禁。

## 12. Agent 与报告（V5.5，已定档待开发）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/v1/store-workspaces/{id}/agent-runs` | 手动运行授权 Agent 工作流 |
| GET | `/v1/store-workspaces/{id}/agent-runs/{run_id}` | 查询步骤、版本和结果 |
| GET | `/v1/store-workspaces/{id}/reports` | 查询日报、周报、月报和告警 |

Agent 接口不接受任意 SQL、任意工具名、文件系统路径、模型地址或写适配器参数。服务端从版本化注册表选择工作流和只读工具，并记录事实、工作流、模型和提示词版本。

## 13. 接口验收规则

- 当前实现与目标契约在文档和测试中明确区分。
- API 与 RLS 均拒绝跨组织/工作区访问。
- 所有分页稳定、错误可分类、请求可追踪且敏感字段不泄露。
- 幂等重试不会生成重复事实或重复执行命令。
- 异步状态来自 PostgreSQL，Redis 清空不丢任务事实。
- 自动化测试不访问真实 Ozon、真实公开页面或真实模型服务。
# 当前认证产品边界

当前系统绑定单一运营组织。`POST /v1/auth/login` 只接收 `email` 和 `password`；组织 ID 由服务端 `DEFAULT_ORGANIZATION_ID` 注入，客户端提交组织请求头、查询参数或请求体字段均不能改变数据边界。`GET /v1/auth/me` 返回用户基本信息和运营角色，不返回供用户切换的组织信息。

当前不提供组织注册、邀请、切换、成员管理和工作区成员授权管理接口。数据库 RLS 仍使用内部组织上下文进行纵深防护。
## 2026-08-09 开发状态同步

- 商品、库存、订单和履约快照历史查询接口已形成 Stub/PostgreSQL 闭环，默认使用稳定分页并限制最大页大小。
- ERP 导入边界要求金额与币种成对出现；缺少币种的金额请求在预览/边界校验阶段拒绝，不写入业务事实。
- Seller 同步 API 当前不调用真实 Ozon；真实适配需在确认官方接口契约和账号授权后接入，禁止从示例路径猜测。
