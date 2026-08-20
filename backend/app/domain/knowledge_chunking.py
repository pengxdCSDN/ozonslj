"""知识型 RAG 的业务感知切片模型与策略注册入口。"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Literal, Protocol

SourceType = Literal["markdown", "postgres_schema", "pdf"]
BusinessDomain = Literal[
    "domain_language",
    "requirements",
    "architecture",
    "api",
    "database",
    "sop",
    "troubleshooting",
    "ozon_official",
    "general",
]
ChunkStatus = Literal["draft", "indexing", "published", "withdrawn", "deleted"]
SensitivityLevel = Literal["public", "internal", "restricted"]
ParsedNodeKind = Literal[
    "heading",
    "paragraph",
    "list",
    "table",
    "code",
    "image_caption",
    "header_footer",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class RawKnowledgeDocument:
    """数据接入层交给解析器的原始文档描述，不携带文件二进制正文。"""

    document_id: str
    source_type: SourceType
    filename: str
    content: str
    content_hash: str
    language: str
    business_domain: BusinessDomain


@dataclass(frozen=True, slots=True)
class ParsedNode:
    """解析器输出的结构节点；切片器只消费节点语义，不依赖具体 PDF/Markdown 库。"""

    kind: ParsedNodeKind
    text: str
    locator: str
    page_from: int | None = None
    page_to: int | None = None
    title_path: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedKnowledgeDocument:
    """统一解析产物，保证 PDF、Markdown 和数据库结构进入同一清洗边界。"""

    document_id: str
    document_version_id: str
    source_type: SourceType
    nodes: tuple[ParsedNode, ...]
    parser_name: str
    parser_version: str


@dataclass(frozen=True, slots=True)
class CleanKnowledgeDocument:
    """通过清洗门禁后的文档；空节点不会进入后续切片和索引。"""

    document_id: str
    document_version_id: str
    source_type: SourceType
    nodes: tuple[ParsedNode, ...]
    cleaner_version: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class ChunkQualityReport:
    """切片质量的确定性报告，供预览、发布门禁和离线评测复用。"""

    chunk_count: int
    empty_count: int
    oversized_count: int
    duplicate_content_count: int
    missing_locator_count: int
    passed: bool


def assess_chunk_quality(
    chunks: Sequence[KnowledgeChunk], *, max_tokens: int, token_counter: TokenCounter | None = None
) -> ChunkQualityReport:
    """检查空正文、超限、重复正文和引用定位；失败时不得进入发布。"""

    counter = token_counter or approximate_token_count
    contents = [chunk.content for chunk in chunks]
    duplicate_count = len(contents) - len(set(contents))
    empty_count = sum(not content.strip() for content in contents)
    oversized_count = sum(counter(content) > max_tokens for content in contents)
    missing_locator_count = sum(not chunk.metadata.source_locator.strip() for chunk in chunks)
    passed = not any(
        (empty_count, oversized_count, duplicate_count, missing_locator_count)
    )
    return ChunkQualityReport(
        chunk_count=len(chunks),
        empty_count=empty_count,
        oversized_count=oversized_count,
        duplicate_content_count=duplicate_count,
        missing_locator_count=missing_locator_count,
        passed=passed,
    )


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """支持过滤、引用、更新、删除和索引重建的最小切片元数据。"""

    document_id: str
    document_version_id: str
    business_domain: BusinessDomain
    source_type: SourceType
    source_level: Literal["a", "b", "c"]
    language: str
    title_path: tuple[str, ...]
    source_locator: str
    chunk_strategy: str
    chunk_strategy_version: str
    status: ChunkStatus = "draft"
    sensitivity: SensitivityLevel = "internal"
    parent_chunk_id: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    extra: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """内容与稳定身份绑定的知识切片；正文变化会产生新的 content_hash。"""

    chunk_id: str
    content: str
    content_hash: str
    ordinal: int
    metadata: ChunkMetadata


@dataclass(frozen=True, slots=True)
class ChunkingRequest:
    """统一多策略切片入口的输入；调用方不能绕过策略注册表。"""

    content: str
    metadata: ChunkMetadata
    target_tokens: int = 420
    max_tokens: int = 520
    overlap_tokens: int = 70


@dataclass(frozen=True, slots=True)
class PdfPage:
    """PDF 提取后的单页文本和版面提示；不携带原始二进制文件。"""

    page_number: int
    text: str
    layout_blocks: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PdfChunkingRequest:
    """PDF 多策略入口；页面抽取与业务切片相互隔离。"""

    pages: tuple[PdfPage, ...]
    metadata: ChunkMetadata
    target_tokens: int = 420
    max_tokens: int = 520
    overlap_tokens: int = 60


class ChunkStrategy(Protocol):
    """定义普通文本切片策略的名称、版本和执行接口。"""

    @property
    def name(self) -> str: """返回切片策略的稳定名称。"""

    @property
    def version(self) -> str: """返回切片策略的版本标识。"""

    def chunk(self, request: ChunkingRequest) -> list[KnowledgeChunk]:
        """按策略将知识请求切分为有边界的片段。"""


class PdfChunkStrategy(Protocol):
    """定义 PDF 切片策略的名称、版本和页面切分接口。"""

    @property
    def name(self) -> str:
        """返回 PDF 切片策略的稳定名称。"""

    @property
    def version(self) -> str:
        """返回 PDF 切片策略的版本标识。"""

    def chunk_pdf(self, request: PdfChunkingRequest) -> list[KnowledgeChunk]:
        """按页面结构将 PDF 请求切分为知识片段。"""


TokenCounter = Callable[[str], int]


def approximate_token_count(text: str) -> int:
    """在模型 tokenizer 未装配时提供确定性预算；中文字符和英文词分别计数。"""

    cjk_count = len(re.findall(r"[\u3400-\u9fff]", text))
    other_words = len(re.findall(r"[A-Za-z0-9_./:-]+", text))
    return cjk_count + other_words


class ChunkStrategyRegistry:
    """按业务域、来源类型和显式策略名选择版本化切片器。"""

    def __init__(self) -> None:
        """初始化对象依赖和运行时状态。"""
        self._strategies: dict[tuple[BusinessDomain, SourceType, str], ChunkStrategy] = {}
        self._pdf_strategies: dict[tuple[BusinessDomain, str], PdfChunkStrategy] = {}

    def register(
        self,
        *,
        business_domain: BusinessDomain,
        source_type: SourceType,
        strategy: ChunkStrategy,
    ) -> None:
        """执行 register 的业务流程并返回该流程的结果。"""
        key = (business_domain, source_type, strategy.name)
        if key in self._strategies:
            raise ValueError(f"切片策略已注册：{key!r}")
        self._strategies[key] = strategy

    def register_pdf(
        self, *, business_domain: BusinessDomain, strategy: PdfChunkStrategy
    ) -> None:
        """执行 register_pdf 的业务流程并返回该流程的结果。"""
        key = (business_domain, strategy.name)
        if key in self._pdf_strategies:
            raise ValueError(f"PDF 切片策略已注册：{key!r}")
        self._pdf_strategies[key] = strategy

    def chunk(self, request: ChunkingRequest) -> list[KnowledgeChunk]:
        """执行 chunk 的业务流程并返回该流程的结果。"""
        key = (
            request.metadata.business_domain,
            request.metadata.source_type,
            request.metadata.chunk_strategy,
        )
        strategy = self._strategies.get(key)
        if strategy is None:
            raise ValueError(f"没有匹配的切片策略：{key!r}")
        return strategy.chunk(request)

    def chunk_pdf(self, request: PdfChunkingRequest) -> list[KnowledgeChunk]:
        """执行 chunk_pdf 的业务流程并返回该流程的结果。"""
        if request.metadata.source_type != "pdf":
            raise ValueError("PDF 切片请求的 source_type 必须为 pdf")
        key = (request.metadata.business_domain, request.metadata.chunk_strategy)
        strategy = self._pdf_strategies.get(key)
        if strategy is None:
            raise ValueError(f"没有匹配的 PDF 切片策略：{key!r}")
        return strategy.chunk_pdf(request)


@dataclass(frozen=True, slots=True)
class MarkdownSectionStrategy:
    """按 Markdown 标题结构切片，过长章节再按段落递归拆分。"""

    name: str = "markdown_sections"
    version: str = "1"
    token_counter: TokenCounter = field(default=approximate_token_count, compare=False)

    def chunk(self, request: ChunkingRequest) -> list[KnowledgeChunk]:
        """执行 chunk 的业务流程并返回该流程的结果。"""
        _validate_request(request)
        sections = _markdown_sections(request.content, request.metadata.title_path)
        pieces: list[tuple[str, tuple[str, ...], str]] = []
        for title_path, body, locator in sections:
            for piece in _split_paragraphs(
                body,
                max_tokens=request.max_tokens,
                overlap_tokens=request.overlap_tokens,
                token_counter=self.token_counter,
            ):
                pieces.append((piece, title_path, locator))
        return _build_chunks(request.metadata, pieces)


@dataclass(frozen=True, slots=True)
class SqlSchemaStrategy:
    """把一张表的说明作为父语境，并按字段/约束形成可检索子切片。"""

    name: str = "postgres_table_fields"
    version: str = "1"

    def chunk(self, request: ChunkingRequest) -> list[KnowledgeChunk]:
        """执行 chunk 的业务流程并返回该流程的结果。"""
        _validate_request(request)
        blocks = [block.strip() for block in re.split(r"\n\s*\n", request.content) if block.strip()]
        if not blocks:
            return []
        table_context = blocks[0]
        pieces = [(table_context, request.metadata.title_path, request.metadata.source_locator)]
        for index, block in enumerate(blocks[1:], start=1):
            pieces.append(
                (
                    f"{table_context}\n\n{block}",
                    request.metadata.title_path,
                    f"{request.metadata.source_locator}#field-{index}",
                )
            )
        return _build_chunks(request.metadata, pieces)


@dataclass(frozen=True, slots=True)
class PdfPageStrategy:
    """按页切分 PDF，适合页码引用严格的规章和合同式资料。"""

    name: str = "pdf_pages"
    version: str = "1"

    def chunk_pdf(self, request: PdfChunkingRequest) -> list[KnowledgeChunk]:
        """执行 chunk_pdf 的业务流程并返回该流程的结果。"""
        pieces = [
            (
                page.text.strip(),
                request.metadata.title_path,
                f"{request.metadata.source_locator}#page={page.page_number}",
                page.page_number,
                page.page_number,
            )
            for page in request.pages
            if page.text.strip()
        ]
        return _build_pdf_chunks(request.metadata, pieces)


@dataclass(frozen=True, slots=True)
class PdfParagraphStrategy:
    """跨页按段落聚合 PDF，适合连续叙述的 SOP、指南和研究资料。"""

    name: str = "pdf_paragraphs"
    version: str = "1"
    token_counter: TokenCounter = field(default=approximate_token_count, compare=False)

    def chunk_pdf(self, request: PdfChunkingRequest) -> list[KnowledgeChunk]:
        """执行 chunk_pdf 的业务流程并返回该流程的结果。"""
        pieces: list[tuple[str, tuple[str, ...], str, int, int]] = []
        for page in request.pages:
            for piece in _split_paragraphs(
                page.text,
                max_tokens=request.max_tokens,
                overlap_tokens=request.overlap_tokens,
                token_counter=self.token_counter,
            ):
                pieces.append(
                    (
                        piece,
                        request.metadata.title_path,
                        f"{request.metadata.source_locator}#page={page.page_number}",
                        page.page_number,
                        page.page_number,
                    )
                )
        return _build_pdf_chunks(request.metadata, pieces)


@dataclass(frozen=True, slots=True)
class PdfLayoutStrategy:
    """优先保留提取器识别的版面块，适合表格、分栏和图文混排 PDF。"""

    name: str = "pdf_layout_blocks"
    version: str = "1"

    def chunk_pdf(self, request: PdfChunkingRequest) -> list[KnowledgeChunk]:
        """执行 chunk_pdf 的业务流程并返回该流程的结果。"""
        pieces: list[tuple[str, tuple[str, ...], str, int, int]] = []
        for page in request.pages:
            blocks = page.layout_blocks or tuple(
                block.strip() for block in re.split(r"\n\s*\n", page.text) if block.strip()
            )
            for block_index, block in enumerate(blocks, start=1):
                pieces.append(
                    (
                        block,
                        request.metadata.title_path,
                        (
                            f"{request.metadata.source_locator}#page={page.page_number}"
                            f"&block={block_index}"
                        ),
                        page.page_number,
                        page.page_number,
                    )
                )
        return _build_pdf_chunks(request.metadata, pieces)


def build_default_chunk_registry() -> ChunkStrategyRegistry:
    """创建首期默认策略注册表；业务新增策略必须显式注册并版本化。"""

    registry = ChunkStrategyRegistry()
    markdown = MarkdownSectionStrategy()
    markdown_domains: tuple[BusinessDomain, ...] = (
        "domain_language",
        "requirements",
        "architecture",
        "api",
        "sop",
        "troubleshooting",
        "ozon_official",
        "general",
    )
    for domain in markdown_domains:
        registry.register(
            business_domain=domain, source_type="markdown", strategy=markdown
        )
    registry.register(
        business_domain="database",
        source_type="postgres_schema",
        strategy=SqlSchemaStrategy(),
    )
    pdf_domains: tuple[BusinessDomain, ...] = (
        "requirements",
        "architecture",
        "api",
        "database",
        "sop",
        "troubleshooting",
        "ozon_official",
        "general",
    )
    for domain in pdf_domains:
        registry.register_pdf(business_domain=domain, strategy=PdfPageStrategy())
        registry.register_pdf(business_domain=domain, strategy=PdfParagraphStrategy())
        registry.register_pdf(business_domain=domain, strategy=PdfLayoutStrategy())
    return registry


def _validate_request(request: ChunkingRequest) -> None:
    """执行内部步骤 _validate_request，供同一模块的公开流程复用。"""
    if not request.content.strip():
        raise ValueError("知识正文不能为空")
    if request.target_tokens < 50 or request.max_tokens < request.target_tokens:
        raise ValueError("切片 token 参数不合法")
    if request.overlap_tokens < 0 or request.overlap_tokens >= request.max_tokens:
        raise ValueError("切片重叠必须非负且小于最大 token")


def _markdown_sections(
    content: str, base_path: tuple[str, ...]
) -> list[tuple[tuple[str, ...], str, str]]:
    """执行内部步骤 _markdown_sections，供同一模块的公开流程复用。"""
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    headings: list[str] = list(base_path)
    current_lines: list[str] = []
    sections: list[tuple[tuple[str, ...], str, str]] = []

    def flush() -> None:
        """执行 flush 的业务流程并返回该流程的结果。"""
        body = "\n".join(current_lines).strip()
        if body:
            locator = "#" + "/".join(headings) if headings else "#document"
            sections.append((tuple(headings), body, locator))
        current_lines.clear()

    for line in content.splitlines():
        match = heading_pattern.match(line)
        if match is None:
            current_lines.append(line)
            continue
        flush()
        level = len(match.group(1))
        heading_index = len(base_path) + level - 1
        del headings[heading_index:]
        while len(headings) < heading_index:
            headings.append("未命名章节")
        headings.append(match.group(2).strip())
    flush()
    return sections


def _split_paragraphs(
    text: str,
    *,
    max_tokens: int,
    overlap_tokens: int,
    token_counter: TokenCounter,
) -> list[str]:
    """执行内部步骤 _split_paragraphs，供同一模块的公开流程复用。"""
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    if not paragraphs:
        return []
    result: list[str] = []
    current: list[str] = []
    for paragraph in paragraphs:
        if token_counter(paragraph) > max_tokens:
            if current:
                result.append("\n\n".join(current))
                current = _overlap_tail(current, overlap_tokens, token_counter)
            result.extend(
                _split_atomic_text(
                    paragraph,
                    max_tokens=max_tokens,
                    token_counter=token_counter,
                )
            )
            continue
        candidate = "\n\n".join([*current, paragraph])
        if current and token_counter(candidate) > max_tokens:
            result.append("\n\n".join(current))
            current = _overlap_tail(current, overlap_tokens, token_counter)
        current.append(paragraph)
    if current:
        result.append("\n\n".join(current))
    return result


def _split_atomic_text(
    text: str, *, max_tokens: int, token_counter: TokenCounter
) -> list[str]:
    """拆分无法再按段落拆分的超长块，优先保留句子边界，最后才按词切分。"""

    units = [unit.strip() for unit in re.split(r"(?<=[。！？.!?])\s+|\n+", text) if unit.strip()]
    if not units:
        return []
    result: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current} {unit}".strip()
        if current and token_counter(candidate) > max_tokens:
            result.append(current)
            current = ""
        if token_counter(unit) <= max_tokens:
            current = f"{current} {unit}".strip()
            continue
        words = unit.split()
        if len(words) == 1:
            # 中文连续文本可能没有空格，按字符切分以确保硬上限可执行。
            words = list(unit)
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and token_counter(candidate) > max_tokens:
                result.append(current)
                current = ""
            current = f"{current} {word}".strip()
    if current:
        result.append(current)
    return result


def _overlap_tail(
    paragraphs: Sequence[str], overlap_tokens: int, token_counter: TokenCounter
) -> list[str]:
    """执行内部步骤 _overlap_tail，供同一模块的公开流程复用。"""
    if overlap_tokens == 0:
        return []
    tail: list[str] = []
    for paragraph in reversed(paragraphs):
        candidate = [paragraph, *tail]
        if tail and token_counter("\n\n".join(candidate)) > overlap_tokens:
            break
        tail = candidate
    return tail


def _build_chunks(
    metadata: ChunkMetadata,
    pieces: Iterable[tuple[str, tuple[str, ...], str]],
) -> list[KnowledgeChunk]:
    """执行内部步骤 _build_chunks，供同一模块的公开流程复用。"""
    chunks: list[KnowledgeChunk] = []
    for ordinal, (content, title_path, locator) in enumerate(pieces):
        normalized = content.strip()
        if not normalized:
            continue
        content_hash = sha256(normalized.encode("utf-8")).hexdigest()
        chunk_id = _chunk_id(metadata, title_path, ordinal, content_hash)
        chunk_metadata = _replace_metadata(
            metadata, title_path=title_path, source_locator=locator
        )
        chunks.append(KnowledgeChunk(chunk_id, normalized, content_hash, ordinal, chunk_metadata))
    return chunks


def _build_pdf_chunks(
    metadata: ChunkMetadata,
    pieces: Iterable[tuple[str, tuple[str, ...], str, int, int]],
) -> list[KnowledgeChunk]:
    """执行内部步骤 _build_pdf_chunks，供同一模块的公开流程复用。"""
    chunks: list[KnowledgeChunk] = []
    for ordinal, (content, title_path, locator, page_from, page_to) in enumerate(pieces):
        normalized = content.strip()
        if not normalized:
            continue
        content_hash = sha256(normalized.encode("utf-8")).hexdigest()
        chunk_id = _chunk_id(metadata, title_path, ordinal, content_hash)
        chunk_metadata = _replace_metadata(
            metadata,
            title_path=title_path,
            source_locator=locator,
            page_from=page_from,
            page_to=page_to,
        )
        chunks.append(KnowledgeChunk(chunk_id, normalized, content_hash, ordinal, chunk_metadata))
    return chunks


def _replace_metadata(
    metadata: ChunkMetadata,
    *,
    title_path: tuple[str, ...],
    source_locator: str,
    page_from: int | None = None,
    page_to: int | None = None,
) -> ChunkMetadata:
    """执行内部步骤 _replace_metadata，供同一模块的公开流程复用。"""
    return ChunkMetadata(
        document_id=metadata.document_id,
        document_version_id=metadata.document_version_id,
        business_domain=metadata.business_domain,
        source_type=metadata.source_type,
        source_level=metadata.source_level,
        language=metadata.language,
        title_path=title_path,
        source_locator=source_locator,
        chunk_strategy=metadata.chunk_strategy,
        chunk_strategy_version=metadata.chunk_strategy_version,
        status=metadata.status,
        sensitivity=metadata.sensitivity,
        parent_chunk_id=metadata.parent_chunk_id,
        effective_from=metadata.effective_from,
        effective_to=metadata.effective_to,
        page_from=page_from,
        page_to=page_to,
        extra=metadata.extra,
    )


def _chunk_id(
    metadata: ChunkMetadata,
    title_path: tuple[str, ...],
    ordinal: int,
    content_hash: str,
) -> str:
    """执行内部步骤 _chunk_id，供同一模块的公开流程复用。"""
    identity = "|".join(
        (
            metadata.document_id,
            metadata.document_version_id,
            "/".join(title_path),
            str(ordinal),
            content_hash,
        )
    )
    return sha256(identity.encode("utf-8")).hexdigest()
