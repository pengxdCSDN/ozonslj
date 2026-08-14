"""PDF 接入前的确定性安全门禁，不执行文件内容。"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PdfSafetyResult:
    status: str
    byte_size: int
    page_count: int | None
    blocked_reason: str | None
    structural_safety_status: str
    malware_scan_status: str


def validate_pdf_upload(
    *, filename: str, declared_mime: str, content: bytes,
    max_bytes: int = 25 * 1024 * 1024, max_pages: int = 300,
) -> PdfSafetyResult:
    """文件先隔离；未配置杀毒服务时不得显示为安全通过。"""

    if len(content) > max_bytes:
        return _blocked(len(content), "文件超过 25 MiB 限制")
    if not filename.lower().endswith(".pdf") or declared_mime != "application/pdf":
        return _blocked(len(content), "扩展名和 MIME 必须同时为 PDF")
    if not content.startswith(b"%PDF-"):
        return _blocked(len(content), "文件不具备 PDF 魔数")
    if re.search(rb"/JavaScript|/Launch|/EmbeddedFile|/OpenAction", content, re.IGNORECASE):
        return _blocked(len(content), "检测到 PDF 脚本、启动动作或嵌入附件")
    page_count = len(re.findall(rb"/Type\s*/Page(?:\s|/)", content)) or None
    if page_count is not None and page_count > max_pages:
        return _blocked(len(content), "PDF 页数超过 300 页限制")
    return PdfSafetyResult(
        status="quarantined", byte_size=len(content), page_count=page_count,
        blocked_reason=None, structural_safety_status="passed",
        malware_scan_status="not_configured",
    )


def _blocked(byte_size: int, reason: str) -> PdfSafetyResult:
    return PdfSafetyResult(
        status="blocked", byte_size=byte_size, page_count=None, blocked_reason=reason,
        structural_safety_status="blocked", malware_scan_status="not_run",
    )
