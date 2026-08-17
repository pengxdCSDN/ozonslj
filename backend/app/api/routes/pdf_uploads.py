"""PDF 隔离上传 API；原始文件只写入服务端隔离目录，不自动解析。"""

from __future__ import annotations

import asyncio
import base64
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.domain.pdf_upload_security import (
    quarantine_pdf,
    quarantined_pdf_path,
    validate_pdf_upload,
)
from backend.app.infrastructure.ocr.paddleocr_document_parser import (
    OcrConfigurationError,
    OcrProviderError,
    parse_pdf,
)

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


class PdfExtractResponse(BaseModel):
    upload_id: str
    status: str
    page_count: int
    extracted_characters: int
    text: str
    blocked_reason: str | None
    text_layer_status: str
    ocr_required: bool
    ocr_provider: str | None


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


@router.post("/{upload_id}/extract-text", response_model=PdfExtractResponse)
async def extract_pdf_text(upload_id: str) -> PdfExtractResponse:
    try:
        path = quarantined_pdf_path(upload_id)
    except (ValueError, FileNotFoundError) as error:
        return PdfExtractResponse(
            upload_id=upload_id, status="blocked", page_count=0,
            extracted_characters=0, text="", blocked_reason=str(error),
            text_layer_status="unavailable", ocr_required=False, ocr_provider=None,
        )
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path), strict=False)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as error:
        return PdfExtractResponse(
            upload_id=upload_id, status="blocked", page_count=0,
            extracted_characters=0, text="", blocked_reason=f"PDF 文本层提取失败：{error}",
            text_layer_status="error", ocr_required=True, ocr_provider=None,
        )
    text = "\n\n".join(page.strip() for page in pages if page.strip()).strip()
    if not text:
        try:
            # PaddleOCR 文档解析可能持续数秒到数分钟；放到线程池，避免阻塞 API 事件循环。
            ocr_document = await asyncio.to_thread(parse_pdf, path)
        except OcrConfigurationError as error:
            return PdfExtractResponse(
                upload_id=upload_id, status="ocr_required", page_count=len(pages),
                extracted_characters=0, text="", blocked_reason=str(error),
                text_layer_status="missing", ocr_required=True, ocr_provider=None,
            )
        except OcrProviderError as error:
            return PdfExtractResponse(
                upload_id=upload_id, status="ocr_failed", page_count=len(pages),
                extracted_characters=0, text="", blocked_reason=str(error),
                text_layer_status="missing", ocr_required=True,
                ocr_provider="paddleocr-doc-parsing",
            )
        return PdfExtractResponse(
            upload_id=upload_id, status="ocr_extracted", page_count=len(ocr_document.pages),
            extracted_characters=len(ocr_document.text), text=ocr_document.text,
            blocked_reason=None, text_layer_status="missing", ocr_required=False,
            ocr_provider=ocr_document.provider,
        )
    # 文本层为空或提取失败才进入 OCR；普通 PDF 不调用外部供应商。
    return PdfExtractResponse(
        upload_id=upload_id, status="extracted", page_count=len(pages),
        extracted_characters=len(text), text=text, blocked_reason=None,
        text_layer_status="available", ocr_required=False, ocr_provider=None,
    )
