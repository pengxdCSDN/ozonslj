"""PDF 接入前的确定性安全门禁，不执行文件内容。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class PdfSafetyResult:
    """说明 PdfSafetyResult 的职责、状态边界和对外协作关系。"""
    status: str
    byte_size: int
    page_count: int | None
    blocked_reason: str | None
    structural_safety_status: str
    malware_scan_status: str


@dataclass(frozen=True, slots=True)
class QuarantinedPdf:
    """说明 QuarantinedPdf 的职责、状态边界和对外协作关系。"""
    upload_id: str
    storage_key: str


def quarantined_pdf_path(upload_id: str, *, root: Path | None = None) -> Path:
    """解析隔离文件路径；只接受 UUID，避免路径穿越。"""

    try:
        safe_id = upload_id if upload_id else str(uuid4())
        uuid = UUID(safe_id)
    except (ValueError, AttributeError):
        raise ValueError("无效的 PDF 隔离文件 ID") from None
    configured_root = os.environ.get(
        "OZONSLJ_PDF_QUARANTINE_DIR", "/var/lib/ozonslj/pdf-quarantine"
    )
    target = (root or Path(configured_root)) / f"{uuid}.pdf"
    if not target.is_file():
        raise FileNotFoundError("PDF 隔离文件不存在")
    return target


def quarantine_pdf(content: bytes, *, root: Path | None = None) -> QuarantinedPdf:
    """写入仅服务端可访问的隔离目录，不返回真实路径。"""

    configured_root = os.environ.get(
        "OZONSLJ_PDF_QUARANTINE_DIR", "/var/lib/ozonslj/pdf-quarantine"
    )
    quarantine_root = root or Path(configured_root)
    quarantine_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    upload_id = str(uuid4())
    target = quarantine_root / f"{upload_id}.pdf"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(target, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
    except Exception:
        try:
            target.unlink(missing_ok=True)
        finally:
            raise
    return QuarantinedPdf(upload_id=upload_id, storage_key=f"quarantine/{upload_id}.pdf")


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
    """执行内部步骤 _blocked，供同一模块的公开流程复用。"""
    return PdfSafetyResult(
        status="blocked", byte_size=byte_size, page_count=None, blocked_reason=reason,
        structural_safety_status="blocked", malware_scan_status="not_run",
    )
