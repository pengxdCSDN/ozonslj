"""说明本模块的职责、边界和主要协作对象。"""

import csv
import hashlib
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from typing import Protocol


@dataclass(frozen=True, slots=True)
class KeywordImportRow:
    """搜索词导入后的内部行模型；不保存原始文件内容。"""

    keyword: str
    search_count: int | None
    conversion_rate: str | None
    source_row: int


@dataclass(frozen=True, slots=True)
class KeywordImportBatch:
    """说明 KeywordImportBatch 的职责、状态边界和对外协作关系。"""
    id: str
    workspace_id: str
    fingerprint: str
    row_count: int
    created_at: datetime
    reused: bool = False


class KeywordImportGateway(Protocol):
    """说明 KeywordImportGateway 的职责、状态边界和对外协作关系。"""
    async def create_batch(
        self, *, workspace_id: str, fingerprint: str, rows: list[KeywordImportRow]
    ) -> KeywordImportBatch:
        """执行 create_batch 的业务流程并返回该流程的结果。"""

    async def list_batches(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[KeywordImportBatch]:
        """执行 list_batches 的业务流程并返回该流程的结果。"""


def keyword_import_fingerprint(content: str) -> str:
    """生成原始导入内容的稳定指纹，供 PostgreSQL 幂等键使用。"""

    return hashlib.sha256(content.encode("utf-8-sig")).hexdigest()


def keyword_import_bytes_fingerprint(content: bytes) -> str:
    """对 XLSX 原始字节计算指纹，保证重复上传命中同一幂等键。"""
    return hashlib.sha256(content).hexdigest()


class KeywordImportError(ValueError):
    """导入文件结构或字段值不符合内部契约。"""


def parse_keyword_csv(
    content: str, column_mapping: dict[str, str] | None = None
) -> list[KeywordImportRow]:
    """解析 UTF-8 CSV 搜索词报告，拒绝空关键词和非法数字。"""

    reader = csv.DictReader(StringIO(content))
    if column_mapping:
        reader = _map_columns(reader, column_mapping)
    required = {"keyword", "search_count", "conversion_rate"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise KeywordImportError("CSV 必须包含 keyword、search_count、conversion_rate 列")
    rows: list[KeywordImportRow] = []
    seen_keywords: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        keyword = (row.get("keyword") or "").strip()
        if not keyword:
            raise KeywordImportError(f"第 {row_number} 行 keyword 为空")
        normalized_keyword = keyword.casefold()
        if normalized_keyword in seen_keywords:
            continue
        seen_keywords.add(normalized_keyword)
        search_count = _parse_non_negative_int(row.get("search_count"), row_number)
        conversion_rate = _parse_conversion_rate(row.get("conversion_rate"), row_number)
        rows.append(KeywordImportRow(keyword, search_count, conversion_rate, row_number))
    return rows


def parse_keyword_xlsx(
    content: bytes, column_mapping: dict[str, str] | None = None
) -> list[KeywordImportRow]:
    """使用标准库读取首个工作表，避免把上传文件交给任意外部执行器。"""
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            shared = _xlsx_shared_strings(archive)
            sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    except (KeyError, ValueError, zipfile.BadZipFile, UnicodeDecodeError) as error:
        raise KeywordImportError("XLSX 文件结构无效") from error
    rows: list[list[str]] = []
    for raw_row in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.DOTALL):
        values: list[str] = []
        for cell in re.findall(r"<c[^>]*?(?:t=\"([^\"]+)\")?[^>]*>(.*?)</c>", raw_row, re.DOTALL):
            cell_type, body = cell
            value_match = re.search(r"<v>(.*?)</v>", body, re.DOTALL)
            value = value_match.group(1) if value_match else ""
            values.append(shared[int(value)] if cell_type == "s" and value.isdigit() else value)
        rows.append(values)
    if not rows:
        raise KeywordImportError("XLSX 不包含工作表数据")
    csv_content = "\n".join(",".join(value.replace(",", " ") for value in row) for row in rows)
    if column_mapping:
        mapped_header = [column_mapping.get(value, value) for value in rows[0]]
        csv_content = "\n".join(
            ",".join(value.replace(",", " ") for value in row)
            for row in [mapped_header, *rows[1:]]
        )
    return parse_keyword_csv(csv_content)


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """执行内部步骤 _xlsx_shared_strings，供同一模块的公开流程复用。"""
    try:
        raw = archive.read("xl/sharedStrings.xml").decode("utf-8")
    except KeyError:
        return []
    return [re.sub(r"<[^>]+>", "", item) for item in re.findall(r"<si>(.*?)</si>", raw, re.DOTALL)]


def _map_columns(
    reader: csv.DictReader[str], column_mapping: dict[str, str]
) -> csv.DictReader[str]:
    """将外部列名映射为内部列名，映射目标必须唯一。"""

    targets = list(column_mapping.values())
    if len(targets) != len(set(targets)):
        raise KeywordImportError("字段映射目标不能重复")
    if not reader.fieldnames or not set(column_mapping).issubset(reader.fieldnames):
        raise KeywordImportError("字段映射包含文件中不存在的列")
    reader.fieldnames = [column_mapping.get(name, name) for name in reader.fieldnames]
    return reader


def _parse_non_negative_int(value: str | None, row_number: int) -> int | None:
    """执行内部步骤 _parse_non_negative_int，供同一模块的公开流程复用。"""
    normalized = (value or "").strip()
    if not normalized:
        return None
    try:
        parsed = int(normalized)
    except ValueError as error:
        raise KeywordImportError(f"第 {row_number} 行 search_count 不是整数") from error
    if parsed < 0:
        raise KeywordImportError(f"第 {row_number} 行 search_count 不能为负数")
    return parsed


def _parse_conversion_rate(value: str | None, row_number: int) -> str | None:
    """校验转化率为 0～100 的百分比，保留原始展示文本便于回溯导入口径。"""
    normalized = (value or "").strip()
    if not normalized:
        return None
    numeric = normalized[:-1].strip() if normalized.endswith("%") else normalized
    try:
        rate = Decimal(numeric)
    except InvalidOperation as error:
        raise KeywordImportError(f"第 {row_number} 行 conversion_rate 不是有效百分比") from error
    if not rate.is_finite() or rate < 0 or rate > 100:
        raise KeywordImportError(f"第 {row_number} 行 conversion_rate 必须在 0% 到 100% 之间")
    return normalized
