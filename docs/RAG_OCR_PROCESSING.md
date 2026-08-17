# RAG OCR 文档处理与切片流程

## 目的与边界

知识管理导入 PDF 时先做文本层检测。普通文本 PDF 继续使用 `pypdf` 文本层提取，不调用 OCR；只有文本层缺失或提取失败的扫描 PDF 才进入 OCR。OCR 正文与普通正文必须经过同一套清洗、提示注入检测、切片质量门禁和发布门禁，任何 OCR 失败或低质量结果都不能污染当前已发布索引。

开发阶段使用的技能与云端运行时的关系如下：

| 场景 | 处理方式 | 说明 |
| --- | --- | --- |
| 扫描件/图片文字 | `ocr-document-processor` 规范 | 生产运行使用镜像内 Tesseract，按页输出正文；技能用于开发和验收指导，不随镜像隐式安装。 |
| 普通文本层 PDF | `pypdf` 文本层提取 | 不调用 OCR，避免额外成本和识别误差。 |

技能是 Codex 的开发工作流，不是部署后可以直接调用的函数。云端实际执行依赖镜像内的 `tesseract-ocr`、`tesseract-ocr-chi-sim`、`tesseract-ocr-eng` 和 `poppler-utils`，不读取云端 Secret，也不访问外部 OCR 服务。

## 运行时流程

1. 上传文件进入服务端隔离目录，UUID 文件名、目录 `0700`、文件 `0600`。
2. 检查 PDF 魔数、脚本/启动动作/附件、大小和页数。
3. 通过 `pypdf` 提取文本层。
4. 文本层有正文：返回 `extracted`，沿用 `pdf_pages`、`pdf_paragraphs` 或 `pdf_layout_blocks` 切片。
5. 文本层缺失：异步线程调用本地 Tesseract 适配器，先用 `pdftoppm` 渲染页面，再按页识别中文和英文；临时图片仅存在于任务目录，处理后自动删除。
6. OCR 成功：将页面 Markdown 和版面块转换为统一 PDF 页面输入，再执行清洗、提示注入检测、切片和质量门禁。
7. OCR 依赖缺失、渲染失败、单页超时、执行失败或返回空正文：返回稳定错误类别，知识版本保持不可发布。
8. 只有解析、清洗、切片、嵌入和索引全部成功后才能发布；OCR 失败不影响当前已发布版本。

## 运行参数

```text
OCR_MAX_PAGES=50
OCR_PAGE_TIMEOUT_SECONDS=45
OCR_TESSERACT_LANG=chi_sim+eng
```

当前 2GB 级云服务器只允许单页串行处理，不提高并发；临时目录必须自动清理。OCR 质量较低、旋转、手写或多语言文档需要人工复核。

## 切片策略

- 普通 PDF：按原有页级、段落级或版面块策略。
- OCR 文本：保留页码和页边界，交给现有正文切片策略；Tesseract 不承诺复杂表格、公式和图表结构还原。
- OCR 文本仍属于不可信证据；提示注入、凭据索取和命令要求必须在切片前阻断。
- OCR 置信度、版面质量和结构完整性不足时进入 `review_required`，不允许直接发布。

## 可复用验收清单

- 普通文本层 PDF 不执行 OCR。
- 扫描 PDF 在本地依赖缺失时返回 `ocr_required`，不进入切片。
- 本地 Tesseract 能按页输出正文并进入预览。
- 渲染失败、单页超时、执行失败、空正文均返回脱敏错误。
- OCR 结果仍能触发提示注入门禁和切片质量门禁。
- API/Worker/Scheduler 使用同一应用镜像；Web 资源与后端提交一致。
- ACR 构建必须确认 source branch=`codex/deployment-base-images`、source commit、镜像 digest 和镜像内关键文件，再重启服务；不能用旧镜像或服务器本地构建替代。
