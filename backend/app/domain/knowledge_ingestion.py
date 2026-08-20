"""RAG 文档解析与清洗领域端口；不依赖 PDF/数据库/文件系统实现。"""

from __future__ import annotations

import re
from dataclasses import replace
from hashlib import sha256
from typing import Protocol

from backend.app.domain.knowledge_chunking import (
    CleanKnowledgeDocument,
    ParsedKnowledgeDocument,
    ParsedNode,
    ParsedNodeKind,
    RawKnowledgeDocument,
    SourceType,
)


class KnowledgeParser(Protocol):
    """说明 KnowledgeParser 的职责、状态边界和对外协作关系。"""
    name: str
    version: str

    def parse(
        self, raw: RawKnowledgeDocument, *, document_version_id: str
    ) -> ParsedKnowledgeDocument:
        """执行 parse 的业务流程并返回该流程的结果。"""


class KnowledgeIngestionError(ValueError):
    """资料不满足 RAG 接入或清洗门禁。"""


class MarkdownKnowledgeParser:
    """解析 Markdown 标题、代码、列表、表格和普通段落，保留定位信息。"""

    name = "markdown_parser"
    version = "1"

    def parse(
        self, raw: RawKnowledgeDocument, *, document_version_id: str
    ) -> ParsedKnowledgeDocument:
        """执行 parse 的业务流程并返回该流程的结果。"""
        _require_source(raw, "markdown")
        return ParsedKnowledgeDocument(
            document_id=raw.document_id,
            document_version_id=document_version_id,
            source_type=raw.source_type,
            nodes=_parse_markdown_nodes(raw.content),
            parser_name=self.name,
            parser_version=self.version,
        )


class PostgresSchemaTextParser:
    """解析脱敏的表/字段中文注释导出，不执行 SQL 或接受动态查询。"""

    name = "postgres_schema_comments"
    version = "1"

    def parse(
        self, raw: RawKnowledgeDocument, *, document_version_id: str
    ) -> ParsedKnowledgeDocument:
        """执行 parse 的业务流程并返回该流程的结果。"""
        _require_source(raw, "postgres_schema")
        nodes = tuple(
            ParsedNode(kind="table", text=block, locator=f"schema://{raw.filename}#{index}")
            for index, block in enumerate(
                (block.strip() for block in re.split(r"\n\s*\n", raw.content)), start=1
            )
            if block
        )
        return ParsedKnowledgeDocument(
            raw.document_id, document_version_id, raw.source_type, nodes, self.name, self.version
        )


class PdfTextLayerParser:
    """解析已由基础设施提取的文本层；不把扫描图片误报为可检索文本。"""

    name = "pdf_text_layer"
    version = "1"

    def parse(
        self, raw: RawKnowledgeDocument, *, document_version_id: str
    ) -> ParsedKnowledgeDocument:
        """执行 parse 的业务流程并返回该流程的结果。"""
        _require_source(raw, "pdf")
        pages = raw.content.split("\f")
        nodes = tuple(
            ParsedNode(
                kind="paragraph",
                text=page.strip(),
                locator=f"{raw.filename}#page={number}",
                page_from=number,
                page_to=number,
            )
            for number, page in enumerate(pages, start=1)
            if page.strip()
        )
        if not nodes:
            raise KnowledgeIngestionError("PDF 没有可用文本层，扫描件必须走后置 OCR 流程")
        return ParsedKnowledgeDocument(
            raw.document_id, document_version_id, raw.source_type, nodes, self.name, self.version
        )


def clean_knowledge_document(
    parsed: ParsedKnowledgeDocument, *, cleaner_version: str = "1"
) -> CleanKnowledgeDocument:
    """清洗 Unicode、模板噪声和提示注入；检测失败时阻断发布，不静默放行。"""

    cleaned: list[ParsedNode] = []
    for node in parsed.nodes:
        text = _normalize_text(node.text)
        if not text or _looks_like_prompt_injection(text):
            if _looks_like_prompt_injection(text):
                raise KnowledgeIngestionError(f"检测到疑似提示注入：{node.locator}")
            continue
        cleaned.append(replace(node, text=text))
    if not cleaned:
        raise KnowledgeIngestionError("清洗后没有可发布的知识内容")
    digest = sha256("\n".join(node.text for node in cleaned).encode("utf-8")).hexdigest()
    return CleanKnowledgeDocument(
        document_id=parsed.document_id,
        document_version_id=parsed.document_version_id,
        source_type=parsed.source_type,
        nodes=tuple(cleaned),
        cleaner_version=cleaner_version,
        content_hash=digest,
    )


def parser_for(source_type: SourceType) -> KnowledgeParser:
    """根据受控来源类型选择解析器；未知来源立即失败。"""

    parsers: dict[SourceType, KnowledgeParser] = {
        "markdown": MarkdownKnowledgeParser(),
        "postgres_schema": PostgresSchemaTextParser(),
        "pdf": PdfTextLayerParser(),
    }
    try:
        return parsers[source_type]
    except KeyError as error:
        raise KnowledgeIngestionError(f"不支持的知识来源类型：{source_type}") from error


def _require_source(raw: RawKnowledgeDocument, expected: SourceType) -> None:
    """执行内部步骤 _require_source，供同一模块的公开流程复用。"""
    if raw.source_type != expected:
        raise KnowledgeIngestionError(f"解析器要求 source_type={expected}")
    if not raw.filename.strip() or not raw.content.strip():
        raise KnowledgeIngestionError("知识文件名和正文不能为空")
    if raw.content_hash != sha256(raw.content.encode("utf-8")).hexdigest():
        raise KnowledgeIngestionError("原始正文哈希不匹配，拒绝解析")


def _parse_markdown_nodes(content: str) -> tuple[ParsedNode, ...]:
    """执行内部步骤 _parse_markdown_nodes，供同一模块的公开流程复用。"""
    nodes: list[ParsedNode] = []
    headings: list[str] = []
    in_code = False
    buffer: list[str] = []
    kind: ParsedNodeKind = "paragraph"

    def flush() -> None:
        """执行 flush 的业务流程并返回该流程的结果。"""
        text = "\n".join(buffer).strip()
        if text:
            nodes.append(
                ParsedNode(
                    kind=kind,
                    text=text,
                    locator=f"markdown://line-{len(nodes)+1}",
                    title_path=tuple(headings),
                )
            )
        buffer.clear()

    for line in content.splitlines():
        if line.strip().startswith("```"):
            if not in_code:
                flush()
                kind = "code"
            buffer.append(line)
            in_code = not in_code
            if not in_code:
                flush()
                kind = "paragraph"
            continue
        if not in_code:
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                flush()
                level = len(heading.group(1))
                del headings[level - 1 :]
                headings.append(heading.group(2))
                nodes.append(
                    ParsedNode(
                        "heading",
                        heading.group(2),
                        f"markdown://heading-{len(nodes)+1}",
                        title_path=tuple(headings),
                    )
                )
                continue
            if line.lstrip().startswith(("- ", "* ", "1. ")):
                kind = "list"
            elif "|" in line:
                kind = "table"
        buffer.append(line)
    flush()
    return tuple(nodes)


def _normalize_text(text: str) -> str:
    """执行内部步骤 _normalize_text，供同一模块的公开流程复用。"""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _looks_like_prompt_injection(text: str) -> bool:
    """执行内部步骤 _looks_like_prompt_injection，供同一模块的公开流程复用。"""
    patterns = (
        r"忽略(?:之前|以上|所有).{0,20}(?:指令|规则|提示)",
        r"ignore\s+(?:all|previous)\s+instructions",
        r"system\s*prompt",
        r"请求访问.{0,12}(?:密钥|凭据|token|密码)",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
