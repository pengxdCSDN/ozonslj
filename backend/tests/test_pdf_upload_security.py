import base64

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes.pdf_uploads import router
from backend.app.domain.pdf_upload_security import validate_pdf_upload


def test_pdf_requires_magic_and_blocks_active_content() -> None:
    assert validate_pdf_upload(
        filename="a.pdf", declared_mime="application/pdf", content=b"not-pdf"
    ).status == "blocked"
    assert validate_pdf_upload(
        filename="a.pdf", declared_mime="application/pdf", content=b"%PDF-1.7 /JavaScript"
    ).status == "blocked"


def test_pdf_upload_enters_quarantine_without_claiming_antivirus_pass() -> None:
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
