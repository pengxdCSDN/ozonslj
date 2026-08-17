# RAG OCR 文档处理与切片流程

## 目的与边界

知识管理导入 PDF 时先做文本层检测。普通文本 PDF 继续使用 `pypdf` 文本层提取，不调用 OCR；只有文本层缺失或提取失败的扫描 PDF 才进入 OCR。OCR 正文与普通正文必须经过同一套清洗、提示注入检测、切片质量门禁和发布门禁，任何 OCR 失败或低质量结果都不能污染当前已发布索引。

开发阶段使用的技能与云端运行时的关系如下：

| 场景 | 处理方式 | 说明 |
| --- | --- | --- |
| 简单扫描件/图片文字 | `ocr-document-processor` 规范 | 适合通用 OCR、纯文本和低结构输入；技能脚本用于开发验证，不随镜像隐式安装。 |
| 表格、多栏、公式、图表和复杂 PDF | `paddleocr-doc-parsing` 规范 | 云端通过 PaddleOCR 文档解析 HTTPS API 适配器执行，输出页面 Markdown 和版面块。 |
| 普通文本层 PDF | `pypdf` 文本层提取 | 不调用 OCR，避免额外成本和识别误差。 |

技能是 Codex 的开发工作流，不是部署后可以直接调用的函数。云端实际执行依赖 `PADDLEOCR_DOC_PARSING_API_URL` 和 `PADDLEOCR_ACCESS_TOKEN`（或 Secret 文件）；未配置时接口返回 `ocr_required`，页面明确提示配置要求，不伪造正文。

## 运行时流程

1. 上传文件进入服务端隔离目录，UUID 文件名、目录 `0700`、文件 `0600`。
2. 检查 PDF 魔数、脚本/启动动作/附件、大小和页数。
3. 通过 `pypdf` 提取文本层。
4. 文本层有正文：返回 `extracted`，沿用 `pdf_pages`、`pdf_paragraphs` 或 `pdf_layout_blocks` 切片。
5. 文本层缺失：异步线程调用 PaddleOCR 文档解析适配器；请求仅发送隔离文件，凭据不进入日志、正文、Chroma 或前端存储。
6. OCR 成功：将页面 Markdown 和版面块转换为统一 PDF 页面输入，再执行清洗、提示注入检测、切片和质量门禁。
7. OCR 未配置、超时、限流、认证失败、返回空正文或结构无效：返回稳定错误类别，知识版本保持不可发布。
8. 只有解析、清洗、切片、嵌入和索引全部成功后才能发布；OCR 失败不影响当前已发布版本。

## 配置契约

```text
PADDLEOCR_DOC_PARSING_API_URL=https://<host>/layout-parsing
PADDLEOCR_ACCESS_TOKEN=<secret-file-or-runtime-secret>
PADDLEOCR_ACCESS_TOKEN_FILE=/run/secrets/paddleocr_access_token
PADDLEOCR_DOC_PARSING_TIMEOUT=600
```

优先使用 Secret 文件，不把令牌写入 `.env`、GitHub、镜像层、浏览器或聊天记录。部署前先用无敏感信息的配置检查确认 URL 为 HTTPS 且以 `/layout-parsing` 结尾；没有凭据时只验收检测与阻断路径。

## 切片策略

- 普通 PDF：按原有页级、段落级或版面块策略。
- OCR 复杂文档：优先 `pdf_layout_blocks`，保留页码和块定位；表格、公式和图表的结构化 Markdown 不得被拼成无定位大段正文。
- OCR 文本仍属于不可信证据；提示注入、凭据索取和命令要求必须在切片前阻断。
- OCR 置信度、版面质量和结构完整性不足时进入 `review_required`，不允许直接发布。

## 可复用验收清单

- 普通文本层 PDF 不产生 OCR 请求。
- 扫描 PDF 未配置 OCR 时返回 `ocr_required`，不进入切片。
- PaddleOCR 200 响应能映射为页面 Markdown/版面块并进入预览。
- 403、429、5xx、超时、无效 JSON、空正文均返回脱敏错误。
- OCR 结果仍能触发提示注入门禁和切片质量门禁。
- API/Worker/Scheduler 使用同一应用镜像；Web 资源与后端提交一致。
- ACR 构建必须确认 source branch=`codex/deployment-base-images`、source commit、镜像 digest 和镜像内关键文件，再重启服务；不能用旧镜像或服务器本地构建替代。

