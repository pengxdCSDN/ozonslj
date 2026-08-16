# RAG HTTP API 目标契约

> 状态：已定档待开发。本文描述知识管理、摄取预览、查询、追踪和反馈的目标接口；仓库中不存在这些路由时不得报告为已实现。

## 1. 通用约定

- 路径沿用 `/v1`；知识管理资源使用 `/v1/knowledge-*`，面向用户的问答使用 `/v1/knowledge-answers`。
- 所有接口要求有效登录会话。管理类写接口还必须校验服务端角色并执行 CSRF 防护。
- 所有响应携带 `X-Request-ID`；异步操作返回任务 ID、状态和轮询地址。
- ID 使用服务端生成的不透明标识。客户端不得提交 Chroma Collection、索引后端地址、模型地址或任意文件路径。
- 时间统一为 UTC ISO 8601；枚举字段未知值视为契约错误，不静默转换。
- 原始文件、解析正文、切片正文和模型上下文默认不在列表接口返回。
- 客户端不能选择模型供应商、处理区域、数据保留模式或是否发送完整上下文；服务端按用途执行最小化和供应商策略校验。
- API 错误使用现有统一 `detail` 结构，并增加稳定、非敏感的 RAG 原因代码。

## 2. 权限角色

首期角色映射为：现有 `root` 用户是 `admin`，普通登录运营账号默认是 `operator`，`reviewer` 由 `admin` 显式授予，`reader` 按只读需要授予。服务端在每次请求读取当前角色，角色变更必须审计，客户端缓存或菜单可见性不构成授权。

| 能力 | reader | operator | reviewer | admin |
|---|---:|---:|---:|---:|
| 查询已发布知识 | 是 | 是 | 是 | 是 |
| 查看来源与引用 | 是 | 是 | 是 | 是 |
| 创建来源/上传候选版本 | 否 | 是 | 是 | 是 |
| 执行解析和切片预览 | 否 | 是 | 是 | 是 |
| 发布通过自动门禁的普通知识 | 否 | 是 | 是 | 是 |
| 提升来源等级、撤回安全风险知识 | 否 | 否 | 是 | 是 |
| 删除、全量重建、修改策略 | 否 | 否 | 否 | 是 |
| 查看脱敏查询追踪 | 否 | 否 | 是 | 是 |
| 配置模型供应商、密钥和用途绑定 | 否 | 否 | 否 | 是 |

首期全局知识不能因为“全局共享”而跳过角色检查。`operator` 可以发布自己提交且通过自动门禁的普通知识，首期不强制双人审核；来源等级提升、敏感/争议资料和安全撤回仍需要 `reviewer/admin`。提交、可选审核和发布动作分别审计，模型和 Agent 不能充当发布主体。

需要人工复核的资源返回 `review_due_at`、`sla_class` 和脱敏升级状态。普通争议/同级冲突为2个工作日，高风险为4小时首次响应且24小时裁决，提示注入/危险文件误报为1个工作日。SLA 到期只触发提醒/升级，不允许客户端或定时任务自动批准、发布或解除隔离。

只读能力接口：`GET /v1/capabilities/knowledge-rag`。响应返回当前用户是否可见知识管理、问答、发布、追踪等能力，以及公开的 `rollout_mode`（`disabled`、`shadow`、`pilot`、`internal`）。接口不返回白名单、其他用户、内部停止原因或服务配置。所有业务接口仍必须独立验证开关，不能信任客户端先前读取的能力结果。

`POST /v1/rag-rollout/transitions` 仅允许 `admin` 请求模式切换。`pilot → internal` 请求包含理由和风险确认，服务端返回试运行时长、真实用户/问题数、AI 增强数、反馈状态和硬门槛结果。运行1天可申请，真实样本不足只产生明确警告；完整冻结验收、安全硬门槛、严重事件或未解决高风险反馈不合格时必须拒绝切换。

单用户部署时 `real_user_count=1` 是合法状态，响应增加 `single_user_deployment=true` 风险说明。服务端按去重后的真实问题统计，不因同一 `root/admin` 兼任多个产品角色而重复计算用户数。

## 3. 知识来源

### 3.1 创建来源

`POST /v1/knowledge-sources`

```json
{
  "display_name": "FBS 库存同步 SOP",
  "source_type": "pdf",
  "business_domain": "sop",
  "language": "zh",
  "effective_from": "2026-08-11T00:00:00Z",
  "effective_to": null,
  "owner_note": "运营团队维护"
}
```

服务端创建 `draft` 来源，普通运营创建时来源等级固定为 C。请求不能指定发布状态、来源等级、审核者、文件系统路径或索引参数；reviewer/admin 通过独立受审计操作授予或提升 A/B。

来源等级变更目标接口：`POST /v1/knowledge-sources/{source_id}/authority-level-changes`，请求包含 `expected_revision`、目标等级和理由。模型、浏览器本地状态和普通发布请求不能隐式改变等级。

### 3.2 列表与详情

- `GET /v1/knowledge-sources?status=&business_domain=&source_type=&cursor=&limit=`
- `GET /v1/knowledge-sources/{source_id}`

列表稳定按 `updated_at DESC, id DESC` 分页。详情返回当前版本、复核时间、解析/索引摘要和允许操作，不返回向量或内部存储路径。

### 3.3 状态操作

- `POST /v1/knowledge-sources/{source_id}/pause`
- `POST /v1/knowledge-sources/{source_id}/resume`
- `POST /v1/knowledge-sources/{source_id}/withdraw`
- `DELETE /v1/knowledge-sources/{source_id}`

每个写操作要求 `expected_revision` 和理由，防止并发覆盖。暂停/撤回先阻断检索，再异步清理派生索引。删除返回清理任务，不承诺同步完成物理删除。

## 4. 文档版本与文件上传

### 4.1 创建版本

`POST /v1/knowledge-sources/{source_id}/versions`

Markdown 和数据库目录型来源可以提交受限内容引用；PDF 使用分阶段上传，避免巨大 multipart 请求长期占用 API Worker。

PDF 目标流程：

1. `POST /v1/knowledge-sources/{source_id}/versions/uploads` 创建受限上传会话；
2. 客户端向服务端授权的私有目标上传；
3. `POST /v1/knowledge-sources/{source_id}/versions/uploads/{upload_id}/complete` 完成哈希、大小、MIME 和签名校验并创建版本。

首期上传目标是服务器私有持久化卷。上传会话只返回不透明 `upload_id`，不能返回服务器目录或最终存储键；服务端完成校验后生成不可预测存储键。未来切换私有对象存储时保持该 API 契约不变。

上传限制包括允许扩展名与 MIME 双重校验、单文件最大 25 MiB、最大 300 页、一次一个文件、加密检测、恶意文件检测、超时和速率限制。同一用户最多同时运行一个 PDF 解析任务。文件名仅用于展示，不作为服务器路径。

上传完成后文件先进入 `quarantined`。服务端结构检查文件签名/MIME、对象/解压/嵌套上限及 JavaScript、Launch Action、嵌入附件、外部资源和密码保护；通过后才能进入 `accepted_for_parse`。响应分别返回 `structural_safety_status` 与 `malware_scan_status`，后者允许 `not_configured`，但界面不得将其显示为已通过。

私有卷达到 85% 时创建上传会话返回 `knowledge_storage_capacity_reached`，但查询、撤回、删除和清理接口继续可用。超过文件或页数上限返回稳定错误并提示人工拆分或压缩，不由服务器自动处理超大文件。

能力接口返回 PDF 接入是否因知识卷低于5 GiB而关闭，不返回宿主机路径或真实剩余字节。删除任务返回 SLA 类别：普通24小时；安全类立即阻断，并显示15分钟在线清理和4小时物理清理目标。备份残留单独显示删除账本状态，不伪装为已立即物理清除。

### 4.2 查询版本

- `GET /v1/knowledge-sources/{source_id}/versions`
- `GET /v1/knowledge-document-versions/{version_id}`

版本详情返回接入、解析、清洗、切片、索引阶段状态以及质量警告。失败响应只给稳定错误类别和安全摘要。

安全摘要包含提示注入扫描状态、风险类别、受影响页码/结构节点和是否阻断，但普通列表不返回可执行攻击正文。人工复核接口只允许 reviewer/admin 对合法安全讨论进行带理由裁决；内容哈希变化后旧裁决自动失效。

## 5. 解析、切片预览与策略

### 5.1 启动解析

`POST /v1/knowledge-document-versions/{version_id}/parse`

```json
{
  "parser_profile": "pdf_layout_auto",
  "force": false,
  "expected_revision": 3
}
```

解析器配置只能从服务端注册表选择。相同内容、解析器版本和配置哈希已成功时返回幂等命中；`force=true` 仅管理员可用且仍创建新的运行记录。

### 5.2 获取解析预览

`GET /v1/knowledge-document-versions/{version_id}/parsed-preview?page=1&node_type=&cursor=&limit=`

返回脱敏结构节点、阅读顺序、页码、标题路径、节点类型、边界框、置信度和警告。图片只返回受控缩略图引用。原始 PDF 不通过该接口公开。

### 5.3 查询可用切片策略

`GET /v1/knowledge-chunk-strategies?source_type=pdf&business_domain=sop`

返回策略名称、版本、适用条件、参数 Schema、默认值、允许范围、成本等级和所需版面结构。首期策略注册表不得提供可发布的 OCR 策略；已弃用策略可用于历史复盘，不能新建运行。

### 5.4 创建切片预览

`POST /v1/knowledge-document-versions/{version_id}/chunk-previews`

```json
{
  "strategy_name": "pdf_paragraphs",
  "strategy_version": "1",
  "parameters": {
    "target_tokens": 420,
    "max_tokens": 520,
    "overlap_tokens": 60
  }
}
```

响应返回异步运行 ID。参数必须通过策略 Schema 校验；不能提交类名、模块路径或代码。

### 5.5 查看切片预览和质量报告

- `GET /v1/knowledge-chunk-runs/{run_id}`
- `GET /v1/knowledge-chunk-runs/{run_id}/chunks?cursor=&limit=`
- `GET /v1/knowledge-chunk-runs/{run_id}/quality-report`

切片预览返回标题路径、页码、token 数、结构类型、内容摘要、父子关系和警告。质量报告返回长度分布、重复率、孤立短片率、超长率、结构保留率和阻断项。

## 6. 审核、发布、撤回与重建

- `POST /v1/knowledge-document-versions/{version_id}/submit-review`
- `POST /v1/knowledge-document-versions/{version_id}/approve`
- `POST /v1/knowledge-document-versions/{version_id}/reject`
- `POST /v1/knowledge-document-versions/{version_id}/publish`
- `POST /v1/knowledge-document-versions/{version_id}/withdraw`
- `POST /v1/knowledge-indexes/rebuilds`

审核和发布请求均包含 `expected_revision`、理由和目标切片运行 ID。普通知识不要求独立审核人，但发布只接受自动安全/质量门禁通过且索引验证成功的版本；需要复核的资料还必须具有有效审核记录。索引重建必须指定知识域和原因，不能接受任意 Collection 名称。

发布成功响应示例：

```json
{
  "publication_id": "pub_01...",
  "source_id": "ks_01...",
  "document_version_id": "kdv_01...",
  "index_version_id": "kiv_01...",
  "status": "published",
  "published_at": "2026-08-11T12:00:00Z"
}
```

## 7. 知识查询与回答

### 7.1 创建回答

`POST /v1/knowledge-answers`

```json
{
  "question": "FBS 库存为什么不同步，需要检查什么？",
  "conversation_context": {
    "previous_answer_id": null
  },
  "response_language": "zh"
}
```

客户端不能提交意图、业务域、来源等级、工作区过滤、模型、提示词、Top-K 或拒答阈值。这些由服务端识别和版本化策略决定。

回答响应和脱敏追踪记录使用的 `retrieval_policy_version`。客户端不得覆盖精确/全文/向量候选数、RRF参数、父文档配额、精排数量或证据数量。

回答追踪中的意图片段可以返回置信度区间、路由状态和公开理由代码，但不能返回内部安全规则全文。客户端不能覆盖 `0.85/0.60` 初始阈值或要求“强制回答”；阈值调整只通过服务端版本化策略发布。

响应包含 `query_rewrite_policy_version` 和公开的重写降级状态，但不返回全部内部派生查询或敏感原文。客户端不能覆盖每片段3条、全请求8条和3秒超时预算，也不能要求在线重试。

多跳回答响应包含 `query_plan_policy_version`、各子问题状态、依赖关系和预算停止原因。客户端不能要求增加步骤、深度、候选、精排或证据上限，也不能把失败子问题标记为已完成。

目标响应：

```json
{
  "answer_id": "ka_01...",
  "trace_id": "ktr_01...",
  "status": "partially_answered",
  "segments": [
    {
      "segment_id": "seg_01",
      "intent": "troubleshooting",
      "business_domain": "inventory",
      "status": "answered",
      "answer": "请依次检查……",
      "claims": [
        {
          "claim_id": "claim_01",
          "text": "同步任务必须处于可执行状态。",
          "citation_ids": ["cit_01"],
          "support_status": "supported"
        }
      ]
    }
  ],
  "citations": [
    {
      "citation_id": "cit_01",
      "source_title": "库存同步 SOP",
      "document_version": "2026-08-01",
      "locator": {"page_from": 3, "page_to": 3, "title_path": ["故障排查"]},
      "excerpt": "……",
      "authority_level": "b",
      "effective_at": "2026-08-11T12:00:00Z"
    }
  ],
  "knowledge_gaps": [],
  "conflicts": [],
  "clarification_question": null,
  "degradation": null
}
```

引用摘录设置严格长度上限并执行授权检查。`status=unsupported` 时回答明确说明不知道，不能返回无引用的推测文本。

每个对外声明必须通过 `citation_ids` 表达“声明—证据”映射，并返回 `support_status`。数字、日期、枚举与限制条件的引用应包含精确原文跨度；高风险声明由服务端执行 A 级或两份独立一致 B 级证据规则，客户端不得降低门槛。部分声明未通过时保留已支持声明，并将其余声明标记为 `unsupported`、`needs_clarification` 或 `conflicted`，不得把整段文本伪装为完全有据。

### 7.2 继续澄清

`POST /v1/knowledge-answers/{answer_id}/clarifications`

只恢复原回答中 `needs_clarification` 的片段。服务端验证片段仍属于当前用户、知识版本仍有效，并保留已完成片段，避免重复模型调用。

客户端只提交服务端签发的会话/回答引用和本轮补充文本，不能提交自造的历史声明、来源等级或“已验证”标记。服务端最多读取当前会话最近6轮脱敏结构化摘要，并对继承的实体、条件、`claim_id`、知识版本和权限重新校验；失效或含糊时返回新的最小澄清问题。

`POST /v1/knowledge-conversations/{conversation_id}/reset`

将当前用户的检索上下文标记为已重置，后续问题不再继承旧快照。该操作不删除历史回答、反馈或依法保留的脱敏审计记录，也不能重置其他用户、工作区或会话。

### 7.3 查询引用详情

`GET /v1/knowledge-answers/{answer_id}/citations/{citation_id}`

只返回当前用户有权访问的来源摘要和定位信息。正常替换/过期返回摘录并标记 `historical`；普通纠错撤回返回摘录、`withdrawn_unreliable` 警告和可用替代版本；安全撤回、敏感信息或删除请求返回 `redacted` 审计墓碑，不返回摘录、文件链接或可反推正文的信息。

引用响应必须包含 `source_status`、`display_policy` 和 `replacement_version_id`（如有）。历史回答文本保持不变，但界面必须展示当前来源警告，不能让用户误以为历史结论仍然有效。

## 8. 查询追踪与反馈

- `GET /v1/knowledge-query-traces/{trace_id}`：reviewer/admin 在 30 天明细保留期内查看脱敏执行摘要；operator 无权浏览全局追踪。
- `POST /v1/knowledge-answers/{answer_id}/feedback`：提交 `helpful`、`incorrect`、`outdated_source`、`missing_answer` 或 `citation_mismatch`。
- `GET /v1/knowledge-feedback?status=&reason=&cursor=&limit=`：审核反馈列表。
- `POST /v1/knowledge-feedback/{feedback_id}/resolve`：记录根因、修复动作和回归用例。

普通运营人员通过回答详情和个人反馈接口查看自己的数据，不提供全局追踪列表权限。追踪接口不返回完整会话、完整提示词、模型原始响应、被过滤候选正文、凭据、个人信息或内部文件路径。超过 30 天的追踪详情返回已过期状态，不从聚合指标反推个人查询。

`GET /v1/rag-aggregate-metrics` 仅向 reviewer/admin 返回180天内无正文、无用户标识的时间桶指标；`GET /v1/rag-audit-archives` 仅向 admin 返回归档批次元数据、记录数和哈希验证状态，不直接返回宿主机路径。审计正文读取使用独立受控查询并记录二次审计。

评测案例采用离线任务接口：`POST /v1/rag-evaluation/case-generation-jobs` 创建受控 AI 草稿生成任务，`GET /v1/rag-evaluation/cases` 查看脱敏草稿，`POST /v1/rag-evaluation/cases/{case_id}/confirm` 单条确认，`POST /v1/rag-evaluation/cases/confirm-batch` 批量确认，`POST /v1/rag-evaluation/runs` 启动分层评测。案例状态、确认人和确认时间持久化到 PostgreSQL；固定 400 例通过幂等种子写入，API 重启不得丢失确认状态。生成模型不能调用确认接口；高风险案例确认要求 reviewer/admin。

创建评测运行时 `suite` 只允许 `quick`、`standard` 或 `full`，分别解析为冻结版本中的固定30、120、240例清单；客户端不能提交任意案例 ID 伪装成发布验收。服务端每批最多调度10例，响应返回 `passed/failed/error/skipped/not_run` 计数和游标。目标清单存在未执行、跳过或错误案例时，`gate_status` 不得为 `passed`。

反馈不得直接修改知识、提示词或模型。任何知识修复仍走版本、审核和发布流程。

## 9. 任务接口

解析、切片、嵌入、索引、删除和重建统一使用任务摘要：

```json
{
  "task_id": "kt_01...",
  "task_type": "chunk_preview",
  "status": "running",
  "progress": {"completed": 12, "total": 40, "unit": "pages"},
  "created_at": "2026-08-11T11:58:00Z",
  "updated_at": "2026-08-11T11:58:03Z",
  "retryable": false,
  "error": null
}
```

进度不得伪造精确百分比；未知总量时 `total` 为 `null`。取消只对尚未发布的可中断任务有效。

任务详情来自 PostgreSQL 治理状态，不直接暴露 Redis 消息 ID、Consumer Group 或 Worker主机信息。`rag-worker` 不可用时，普通摄取/索引任务返回可重试的暂停状态；安全撤回、删除请求仍被持久化并以最高优先级等待恢复。

## 9A. 管理员模型供应商配置

以下接口仅允许 `admin`，所有写操作要求 CSRF、`expected_revision`、幂等键、敏感操作再确认和审计：

- `GET /v1/model-providers`：返回供应商 ID、适配器类型、受控 API 地址、启用状态、数据政策摘要、密钥是否配置、末尾掩码、最后验证时间和用途绑定；永不返回 API Key。
- `POST /v1/model-providers`：创建 DeepSeek、MiniMax、GPT 等已注册适配器配置。`api_key` 是只写字段，API 地址必须通过适配器白名单、HTTPS 和 SSRF 校验。
- `PATCH /v1/model-providers/{provider_id}`：修改非敏感配置或提交新的 `api_key` 完成轮换。省略密钥表示保持不变，不能用读取响应中的掩码覆盖真实密钥。
- `POST /v1/model-providers/{provider_id}/connection-tests`：使用固定非敏感载荷异步验证认证、网络、模型存在性与结构化输出，返回任务 ID；不得回显请求头、密钥或供应商原始错误正文。
- `POST /v1/model-providers/{provider_id}/disable`：停止新调用，但保留配置版本和审计引用；已运行任务按用途级超时结束，不自动切换到未审核供应商。
- `DELETE /v1/model-providers/{provider_id}`：仅在无用途绑定、无运行任务且满足审计保留规则时允许；否则返回稳定冲突错误并要求先停用/解绑。
- `GET /v1/model-purpose-bindings` 与 `PUT /v1/model-purpose-bindings/{purpose}`：管理 `embedding`、`translation`、`intent_rewrite`、`rerank`、`answer_generation` 的主模型和可选备用模型。绑定到 `pilot/internal` 前必须验证对应能力已通过 `shadow` 门禁。
- `GET /v1/model-budget-policies` 与 `PUT /v1/model-budget-policies/{provider_id}`：仅管理员查看/配置每日、每月 token 与估算费用预算，以及用途级单请求输入、输出和调用次数上限；写入要求敏感操作确认、乐观并发和审计。
- `GET /v1/model-budget-usage?provider_id=&period=`：返回当前周期已结算、已预留、剩余比例、70%/90%/100% 状态和估算费用；不返回 API Key、完整提示词或用户问题正文。

当前实现说明：额度管理页面已通过 `/v1/model-budgets` 读取持久化策略和用量，并通过
`PUT /v1/model-budgets/{provider_id}` 保存策略；正式 RAG 调用路径按用途执行预算门禁，
成功响应中的 `usage.total_tokens` 和请求次数自动写入 PostgreSQL 台账。`POST /v1/knowledge-answers/query`
在证据门禁通过后调用 `answer_generation` 文本模型，`POST /v1/knowledge-answers/translate` 调用
`translation` 用途；供应商账单用量对账接口仅保留后续适配位。

预算接口以 `Asia/Shanghai` 自然日/月展示周期，同时返回 UTC `period_start`/`period_end`、`billing_currency`、原币种金额和 token。可选 `display_cny` 必须携带参考汇率版本与“仅供展示”标记；客户端不得用折算值判断是否允许调用。时区、币种或预算变更只对下一周期生效。

用途绑定请求只接受一个 `primary_model_ref` 和至多一个 `fallback_model_ref`。服务端拒绝相同引用、能力不匹配、未通过数据策略/`shadow` 门禁，以及嵌入配置不兼容的备用绑定；客户端不能提交第三候选或修改“每请求最多切换一次”的执行上限。

`adapter_type` 首期允许 `deepseek`、`minimax`、`openai` 和 `openai_compatible`。读取接口返回适配器声明的能力，前端据此过滤用途绑定候选，但服务端仍独立验证。`openai_compatible` 创建或修改时要求批准域名；API 对 URL 规范化、DNS、目标网段和每次重定向执行校验。远程模型发现结果只供选择，管理员可以提交显式模型 ID，最终以连通性与 `shadow` 评测记录为准。

密钥创建或轮换成功后只返回 `credential_configured=true`、`credential_mask` 和 `credential_updated_at`。清除密钥必须使用独立显式动作，不能用空字符串表达；存在用途绑定时禁止清除。

API 层只接收一次明文 `api_key` 并立即交给 `HostFileModelCredentialStore`；响应、审计和异常均不得包含明文。存储器在宿主机受限目录以 `0600` 权限原子创建随机文件，PostgreSQL 只保存不透明引用和版本。文件缺失、权限/所有者异常或读取失败时统一将凭据标记为不可用并返回稳定安全错误，不尝试调用供应商。

供应商列表还返回脱敏的 `availability_status`、`circuit_state`、`reason_code`、`cooldown_until` 和最近成功时间。额度/余额/认证错误不得返回供应商原始正文。管理员可以在补充额度或轮换密钥后发起新的连通性测试；只有测试成功且冷却条件满足时才关闭熔断，不能通过客户端直接强制标记健康。

连通性测试支持两种输入：新增配置提交本次请求的 `api_key`；编辑已有配置时可省略 `api_key` 并提交 `provider_id`，服务端先校验该供应商属于当前组织，再从受限凭据目录读取已保存密钥。API Key 永不回显、不会进入响应或日志；若供应商凭据不存在，接口返回可操作的 422，而不是要求前端回读密钥。

数据库或服务器恢复后，宿主机凭据文件未通过存在性、所有者和权限校验的配置返回 `credential_configured=false`、`availability_status=credential_missing`。客户端必须提示管理员重新录入，不能提供“从备份恢复明文密钥”操作；重新录入后仍需完成连通性测试才能启用。

知识回答的 `degradation` 信息返回计划模型引用、实际模型引用、是否发生一次切换及稳定原因代码；不返回 API 地址、账户标识、密钥、请求头或供应商原始错误正文。

## 10. 稳定错误代码

| 错误代码 | HTTP | 含义 |
|---|---:|---|
| `knowledge_source_not_found` | 404 | 来源不存在或不可见 |
| `knowledge_revision_conflict` | 409 | 乐观并发版本不一致 |
| `knowledge_version_not_ready` | 409 | 前置阶段未完成 |
| `knowledge_quality_gate_failed` | 422 | 质量报告存在阻断项 |
| `knowledge_parser_unsupported` | 422 | 文件或解析配置不支持 |
| `knowledge_ocr_review_required` | 422 | 检测到扫描型 PDF；首期不运行 OCR，需人工复核或提供带文本层版本 |
| `knowledge_file_dangerous_feature` | 422 | PDF 包含脚本、启动动作、附件、外部资源或其他首期禁止特性 |
| `knowledge_file_resource_bomb` | 422 | 对象数、解压大小、嵌套深度或沙箱资源超过限制 |
| `knowledge_parser_sandbox_failed` | 503 | 解析沙箱超时、资源终止或异常退出，失败关闭 |
| `knowledge_strategy_not_allowed` | 422 | 策略未注册、已弃用或不适用 |
| `knowledge_prompt_injection_blocked` | 422 | 检测到面向模型的越权、泄密、引用绕过或工具执行内容，需人工复核 |
| `knowledge_prompt_injection_scan_failed` | 503 | 安全检测不可用或高风险无法判断，失败关闭 |
| `knowledge_index_unavailable` | 503 | 治理或关键词检索不可用，不能安全回答 |
| `knowledge_semantic_search_degraded` | 200 | 作为响应降级字段，不单独伪装错误 |
| `model_provider_quota_exhausted` | 200/503 | 有安全降级结果时为响应降级字段；无可用链路时暂不可用 |
| `model_provider_balance_insufficient` | 200/503 | 行为同额度耗尽，且触发管理员告警 |
| `model_provider_rate_limited` | 200/503 | 总预算内最多一次受控重试，否则降级或暂不可用 |
| `embedding_profile_unavailable` | 200/503 | 可精确/全文检索时显式降级，否则暂不可用 |
| `model_budget_soft_warning` | 200 | 达到 70%/90% 时作为管理告警，不影响已允许调用 |
| `model_budget_exhausted` | 200/503 | 主模型硬停止并尝试唯一备用；无安全降级时暂不可用 |
| `model_request_budget_exceeded` | 422 | 单请求 token 或调用次数预计超过用途上限，不发起供应商调用 |
| `knowledge_answer_unsupported` | 200 | 合法的“不知道”终态 |
| `knowledge_request_restricted` | 403 | 请求包含不可执行或越界意图 |
| `knowledge_task_conflict` | 409 | 相同资源已有互斥任务运行 |
| `knowledge_file_too_large` | 413 | PDF 超过 25 MiB |
| `knowledge_page_limit_exceeded` | 422 | PDF 超过 300 页 |
| `knowledge_storage_capacity_reached` | 507 | 私有卷达到停止上传阈值 |

## 11. API 验收条件

1. 所有管理写接口具备角色、CSRF、乐观并发和审计测试。
2. 未发布、已撤回、过期、敏感和无权知识无法通过任何读取或引用接口泄露。
3. 上传、解析、切片和重建任务幂等且可恢复；重复请求不产生重复发布。
4. 多意图回答逐片段返回状态，不把部分成功报告为全部成功。
5. 查询重写、Chroma、精排或生成降级在响应中准确标记。
6. 不知道、冲突和需要澄清均有稳定响应 Schema。
7. 列表均有稳定游标分页和最大页大小。
8. 错误响应不泄露文件路径、模型地址、Collection、凭据或其他组织资源是否存在。

## 12. 首期界面与 API 对应关系

| 界面能力 | 主要 API | 首期状态 |
|---|---|---|
| 来源列表与版本详情 | 知识来源、版本列表/详情 | 必须 |
| Markdown/数据库/PDF 接入 | 来源创建、版本上传与完成 | 必须 |
| 文件隔离与安全状态 | 上传详情、结构检查、恶意软件扫描能力状态 | 必须 |
| 解析结构预览 | parse、parsed-preview | 必须 |
| 切片策略和预览 | strategies、chunk-previews、quality-report | 必须 |
| 发布检查与版本操作 | review/publish/withdraw、任务详情 | 必须 |
| 知识问答与引用 | knowledge-answers、clarifications、citations | 必须 |
| 个人问答历史与反馈 | 当前用户回答列表、feedback | 必须 |
| 全局查询追踪分析 | query-traces | 首期只提供受控 API，不建设完整界面 |
| 管理员模型供应商配置 | model-providers、connection-tests、model-purpose-bindings | 必须，仅 admin |
| 模型预算与当前用量 | model-budget-policies、model-budget-usage | 必须，仅 admin |
| OCR 校对、策略代码、提示词/成本高级运营 | 无客户端可写契约 | 非首期 |

界面不能根据按钮可见性代替服务端权限。所有状态变更请求携带 `expected_revision`；任务轮询使用有限退避和取消机制，页面卸载后停止无用请求。
### 模型额度预算币种

模型额度页面的“月度预算”统一按人民币（RMB）填写和展示。`monthly_budget` 表示人民币金额，不是 token 数量；接口同时返回 `budget_currency: "RMB"`。日/月 token 上限仍以 token 计，三者不得混用。后续如接入供应商原币种，需要增加明确的汇率版本和原币种台账，不能继续使用无单位数字。
