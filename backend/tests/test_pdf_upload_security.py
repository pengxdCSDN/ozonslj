import base64
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.pdf_uploads import router
from backend.app.domain.pdf_upload_security import (
    quarantine_pdf,
    quarantined_pdf_path,
    validate_pdf_upload,
)


def test_pdf_requires_magic_and_blocks_active_content() -> None:
    assert validate_pdf_upload(
        filename="a.pdf", declared_mime="application/pdf", content=b"not-pdf"
    ).status == "blocked"
    assert validate_pdf_upload(
        filename="a.pdf", declared_mime="application/pdf", content=b"%PDF-1.7 /JavaScript"
    ).status == "blocked"


def test_pdf_upload_enters_quarantine_without_claiming_antivirus_pass(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("OZONSLJ_PDF_QUARANTINE_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    payload = base64.b64encode(b"%PDF-1.7\n1 0 obj\n<< /Type /Page >>").decode()
    response = TestClient(app).post(
        "/v1/knowledge-pdf-uploads",
        json={"filename": "guide.pdf", "mime_type": "application/pdf", "content_base64": payload},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "quarantined"
    assert response.json()["malware_scan_status"] == "not_configured"
    assert response.json()["stored_in_quarantine"] is True
    stored = list(tmp_path.glob("*.pdf"))
    assert len(stored) == 1
    assert stored[0].read_bytes().startswith(b"%PDF-")
    if os.name != "nt":
        assert stored[0].stat().st_mode & 0o777 == 0o600


def test_quarantine_uses_unique_non_overwriting_keys(tmp_path: Path) -> None:
    first = quarantine_pdf(b"%PDF-1.7 first", root=tmp_path)
    second = quarantine_pdf(b"%PDF-1.7 second", root=tmp_path)
    assert first.upload_id != second.upload_id
    assert len(list(tmp_path.glob("*.pdf"))) == 2


def test_quarantined_path_rejects_path_traversal(tmp_path: Path) -> None:
    try:
        quarantined_pdf_path("../escape", root=tmp_path)
    except ValueError as error:
        assert "无效" in str(error)
    else:
        raise AssertionError("路径穿越 ID 未被拒绝")
