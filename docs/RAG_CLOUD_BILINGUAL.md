# Ozon 俄文商品云端中文化方案

## 目标

Ozon 返回的商品名称、描述和属性通常为俄文。系统以俄文为上游事实，使用云端翻译生成中文展示副本，并使用云端多语言 Embedding 支持中文问题检索俄文商品。服务器只运行 API、Worker、PostgreSQL 和 Chroma，不运行本地模型。

## 数据规则

1. `name`、`description_ru`、`attributes_ru` 保存 Ozon 原文，禁止被中文覆盖。
2. `name_zh`、`description_zh`、`attributes_zh` 是可重建的派生字段。
3. `translation_source_hash` 记录俄文输入指纹；输入变化后重新翻译。
4. 翻译失败保留俄文，状态为 `failed`，不得用模型猜测缺失字段。
5. 品牌、型号、SKU、价格、尺寸、单位、商品编码和平台状态以结构化原值为准，不进行自由翻译。

## 云端调用

- Embedding 默认使用阿里云百炼 `text-embedding-v4`，维度默认 1024。
- 翻译使用云端 Chat API，支持阿里云百炼或 DeepSeek 等已登记的 OpenAI-compatible 供应商。
- API Key 默认通过服务器 Secret 注入；管理员也可以在“RAG 模型供应商”页面提交，后端会立即写入受限 Secret 卷，不写入前端存储、PostgreSQL、Chroma 元数据、日志或异常文本。
- 供应商返回 429、余额不足或限流时转换为统一额度错误，由用途级备用供应商处理。

## 检索文本

向量输入由以下内容组成：

```text
中文标题
俄文标题
中文描述
俄文描述
中文属性
俄文属性
```

中文问题和俄文关键词都可以命中同一商品。向量模型、维度或预处理规则变化时，必须创建新的索引版本并完整重建，不能在同一 Chroma collection 混用维度。

## 处理时序

```text
Ozon 同步 → 保存俄文事实 → 创建翻译任务 → 云端翻译 → 保存中文副本
→ 生成中俄双语 embedding → 写入新索引版本 → 校验后发布
```

翻译是异步任务，不阻塞商品初次同步。任务按源内容指纹幂等，失败可重试，已成功且源指纹未变化的商品不重复调用供应商。

## 当前实现状态

- 已完成中俄内容领域契约：`backend/app/domain/product_localization.py`。
- 已完成云端 Embedding 和翻译 HTTP 适配器：`backend/app/infrastructure/cloud_models.py`。
- 已完成商品翻译字段迁移：`database/migrations/0095_product_localization.sql`。
- 已支持登记 DashScope 和受控 `base_url`：`database/migrations/0096_rag_provider_base_url.sql`。
- 已完成 MockTransport 契约测试：`backend/tests/test_cloud_models.py`。
- 尚未写入真实 API Key，也未对现有商品执行全量翻译和 1024 维索引重建；这两个动作需要部署环境配置后再执行。

## 服务器 Secret 配置

部署目录为 `deploy/` 时，API 和 Worker 通过 Docker Compose Secret 读取 Key：

```bash
cd deploy
mkdir -p secrets
umask 077
printf '%s' '你的百炼APIKey' > secrets/rag_embedding_api_key
printf '%s' '你的百炼APIKey' > secrets/rag_translation_api_key
```

随后在 `.env` 中只填写供应商、地址、模型和维度，不填写 API Key：

```dotenv
RAG_EMBEDDING_PROVIDER=dashscope
RAG_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
RAG_EMBEDDING_MODEL=text-embedding-v4
RAG_EMBEDDING_DIMENSION=1024
RAG_TRANSLATION_PROVIDER=dashscope
RAG_TRANSLATION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
RAG_TRANSLATION_MODEL=qwen-plus
```

`deploy/compose.yaml` 会把两个文件分别挂载为 `/run/secrets/rag_embedding_api_key` 和 `/run/secrets/rag_translation_api_key`。Secret 文件不能提交 Git、不能写入镜像，也不能在聊天中发送。配置页面提交后无需把 Key 写入 `.env`；部署重启后 API/Worker 会从受限凭据卷读取 Key。

## 模型供应商维护页面

系统工具 → RAG 模型供应商用于维护云端模型和用途级主备绑定。当前确认的路由为：

| 用途 | 主模型 | 备用模型 | 维度 |
| --- | --- | --- | --- |
| Embedding | 阿里云 `text-embedding-v4` | SiliconFlow `BAAI/bge-m3` | 统一 1024 |
| 俄语 → 中文翻译 | SiliconFlow `Qwen/Qwen2.5-7B-Instruct` | 智谱 `glm-4-flash` | 不适用 |

页面提交 API Key 后，后端会以供应商 ID 命名写入受限可写 Secret 卷；PostgreSQL 只保存供应商配置、凭据引用和末四位掩码。页面不会保存 API Key，也不会在响应中回显明文。

默认地址核对入口：

- [SiliconFlow 控制台](https://cloud.siliconflow.cn/)
- [SiliconFlow API 文档](https://docs.siliconflow.cn/)
- [智谱开放平台](https://open.bigmodel.cn/)
- [智谱 API 文档](https://docs.bigmodel.cn/api-reference/)

SiliconFlow 默认 OpenAI-compatible Base URL 为 `https://api.siliconflow.cn/v1`；智谱默认 Base URL 为 `https://open.bigmodel.cn/api/paas/v4`。若控制台显示不同地址，以控制台和官方 API 文档为准。百炼工作空间地址仍使用 `https://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`。

## 模型池、优先级与自动降级

模型供应商配置分为两个互斥模型池：

- `embedding`：只用于向量化、Chroma 写入和语义检索。
- `text`：用于翻译、查询重写、意图识别、重排序和答案生成。

每个模型配置都可以在前端新增、编辑、启用、停用和删除，并记录供应商名称、适配器、模型 ID、Base URL、服务端凭据引用和优先级。优先级使用正整数，数值越小表示优先级越高；同一模型池按 `priority, provider_id` 稳定排序，不依赖页面中的固定示例。

用途路由保存一个主模型和任意数量的备用模型。页面的“按优先级保存”会把当前模型池中所有启用配置写入降级链。运行时按链路逐个尝试：预算门禁会先跳过已超额配置；请求遇到供应商限额、429、超时、网络不可用或其他云模型错误时记录安全错误码并尝试下一项。所有候选均不可用时才返回“模型供应商暂不可用”，不得生成无依据的答案。

API Key 只在新增或更换时从页面提交到服务端 Secret 存储；列表、日志、审计和错误响应只返回配置状态及末四位掩码。删除绑定中的供应商会返回冲突，必须先重新生成用途路由，避免运行时出现悬挂引用。
