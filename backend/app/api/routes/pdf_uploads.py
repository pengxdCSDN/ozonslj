"""PDF 隔离上传 API；原始文件只写入服务端隔离目录，不自动解析。"""

from __future__ import annotations

import base64
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.domain.pdf_upload_security import quarantine_pdf, validate_pdf_upload

router = APIRouter(prefix="/v1/knowledge-pdf-uploads", tags=["knowledge-pdf"])


class PdfUploadPayload(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    mime_type: str = Field(min_length=1, max_length=100)
    content_base64: str = Field(min_length=1, max_length=35_000_000)


class PdfUploadResponse(BaseModel):
    upload_id: str
    status: str
    byte_size: int
    page_count: int | None
    structural_safety_status: str
    malware_scan_status: str
    blocked_reason: str | None
    stored_in_quarantine: bool


@router.post("", response_model=PdfUploadResponse, status_code=202)
async def upload_pdf(payload: PdfUploadPayload) -> PdfUploadResponse:
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except ValueError:
        content = b""
    result = validate_pdf_upload(
        filename=payload.filename, declared_mime=payload.mime_type, content=content
    )
    upload_id = str(uuid4())
    stored = False
    if result.status == "quarantined":
        stored_file = quarantine_pdf(content)
        upload_id = stored_file.upload_id
        stored = True
    return PdfUploadResponse(
        upload_id=upload_id, status=result.status, byte_size=result.byte_size,
        page_count=result.page_count, structural_safety_status=result.structural_safety_status,
        malware_scan_status=result.malware_scan_status, blocked_reason=result.blocked_reason,
        stored_in_quarantine=stored,
    )
