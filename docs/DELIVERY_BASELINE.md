# Ozon Workbench 交付基线

本文档将 `ozon-workbench-delivery-doc.md` 整理为仓库内可执行的需求、架构和开发边界。它是后续阶段 3 开发的补充基线；现有阶段 2 的工作区、凭据和商品缓存能力继续以 `REQUIREMENTS.md`、`ARCHITECTURE-V5.md`、`API.md` 和 `DATABASE.md` 为准。

## 1. 产品边界

平台面向单一 Ozon 平台，数据来源分为三类：

1. Ozon Seller API：店铺私有事实，包括商品、库存、订单、履约、财务和自有销售分析。
2. Ozon Performance API：广告活动、关键词和广告效果报表，使用独立 OAuth 2.0 凭据。
3. 自建公开采集层与卖家后台搜索词报告：竞品公开展示字段和俄语搜索词分析；公开采样数据必须标记为估算。

不接入付费第三方市场数据订阅。公开采集必须遵守 robots.txt、服务条款、限速和退避规则。

## 2. 只读 AI 与人工审核原则

- AI、Agent 和分析模块默认只有读取事实、计算指标、生成草稿、建议、报告和告警的权限。
- 上架、改价、改库存、修改 Listing、广告预算/出价、否定词写入等操作必须进入人工审核队列。
- 审核通过后才能生成一次性、幂等的执行命令；自动化测试永远不访问真实 Ozon 账号。
- 任何结论必须记录来源、采样时间、是否估算、计算假设和数据版本。

## 3. 阶段 3A：选品 MVP（P0）

### 3.1 功能

- `explore`：按搜索词热度和类目公开样本探索机会。
- `validate`：围绕指定 SKU 分析竞品价格、评分、评价数、上架时间、公开卖点和自有销售缺口。
- `expand`：从已有商品或搜索词扩展相关词和类目样本。
- 导入脱敏的卖家后台搜索词报告。
- 维护竞品种子 URL，并采集标题、价格、评分、评价数、主图 URL、公开属性和上架时间等展示字段。
- 生成商品立项决策书草稿：市场容量、竞争快照、利润测算、FBO/FBS 对比、风险清单和行动建议。

### 3.2 明确禁止

选品模块不得自动上架、调价、采购、下单或调用任何写接口。

## 4. 阶段 3B：Listing 与广告（P1）

- Listing 支持俄语核心词、属性词、场景词分层，生成标题、Search Attributes、FABE 卖点和描述草稿。
- 检测重复词、禁用词、未经授权品牌词和认证风险表述；只给建议，不自动删除原文。
- 广告模块独立使用 Performance API，计算 ACOS、TACOS、CPC、CTR、CVR、ROI。
- 广告模块只生成预算、出价和否定词建议，不自动写入 Performance API。

## 5. 阶段 3C：多 Agent 协同（P2）

销售、库存、广告、竞品监控和汇总 Agent 只读运行，输出日报、周报、月报和告警。每个报告必须关联数据快照与分析版本；通知和写入仍需人工审核。

## 6. 目标领域模型

| 实体 | 作用 | 关键约束 |
|---|---|---|
| `research_keywords` | 搜索词报告与关键词分层 | workspace、词文本、报告日期唯一；来源必填 |
| `competitor_seeds` | 运营维护的公开竞品种子 | workspace 内 URL 唯一；仅允许公开 URL |
| `public_product_snapshots` | 公开商品采样快照 | `source=public_sample`；必须有采样时间和估算标记 |
| `product_research_runs` | 三种选品模式的运行记录 | 模式、状态、输入摘要、版本可追踪 |
| `product_decision_documents` | 商品立项决策书草稿 | 关联研究运行，保存假设版本 |
| `listing_drafts` | Listing 草稿和检测结果 | 不直接改变商品事实，必须有审核状态 |
| `review_queue` | 所有外部写入建议 | 默认 pending；记录目标、风险、操作者和确认时间 |
| `performance_credentials` | Performance OAuth 密文 | 与 Seller 凭据完全分离 |
| `ad_campaign_snapshots` | 广告活动与关键词统计 | 按 workspace、活动、日期幂等 upsert |

金额使用最小货币单位整数；订单和广告分析不把买家 PII 写入选品或竞品宽表。

## 7. 目标 API 契约

以下是应用层目标接口，不是 Ozon 上游路径：

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/v1/store-workspaces/{id}/research-runs` | 创建 explore/validate/expand 分析 |
| GET | `/v1/research-runs/{id}` | 查询运行状态与来源摘要 |
| POST | `/v1/store-workspaces/{id}/keyword-reports/import` | 导入脱敏搜索词报告 |
| POST | `/v1/store-workspaces/{id}/competitor-seeds` | 录入公开竞品种子 |
| GET | `/v1/store-workspaces/{id}/product-decisions` | 查询决策书草稿 |
| POST | `/v1/store-workspaces/{id}/listing-drafts` | 生成 Listing 草稿 |
| GET | `/v1/store-workspaces/{id}/ad-analytics` | 查询广告指标和诊断建议 |
| GET | `/v1/store-workspaces/{id}/review-queue` | 查询待审核建议 |
| POST | `/v1/review-queue/{id}/approve` | 人工确认并生成受控命令 |

所有研究、草稿和分析接口默认只读；响应需携带 `source`、`observed_at` 和 `estimated` 等来源元数据。

## 8. 架构落地规则

- `SellerApiClient`、`PerformanceApiClient`、`PublicCatalogCollector` 是三个独立适配器端口。
- Performance API 不复用 Seller API 的认证实现、密钥或域名。
- `ProductResearchService` 编排三种模式；`ProfitCalculator` 只接收整数金额和显式成本假设。
- 建议和草稿属于只读产物；只有 `ReviewQueue` 能把人工确认结果交给写适配器。
- P0 不引入 ClickHouse、向量数据库或常驻爬虫集群；首期使用 PostgreSQL 快照表、Redis 任务队列和受控 Worker，适配 2 核 2GB 部署目标。

## 9. 开发顺序与验收

1. 先迁移关键词、竞品种子、公开快照、研究运行和决策书表。
2. 实现脱敏搜索词报告导入与校验。
3. 实现带 robots、限速、退避和 Mock 契约测试的公开采集端口。
4. 实现 explore、validate、expand、利润测算和决策书草稿。
5. 再开始 Listing、Performance API 和人工审核队列。

阶段 3A 验收要求：一份脱敏搜索词报告和一组竞品种子能够生成可追溯决策书；结果明确区分真实数据与估算数据；测试不访问真实外部账号或网站；任何写入建议停留在人工审核队列。
