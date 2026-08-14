from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.erp_adapter import ErpSupplyRecord, parse_erp_csv

router = APIRouter(prefix="/v1/erp", tags=["erp"])


class ErpCsvPreviewPayload(BaseModel):
    content: str = Field(min_length=1, max_length=2_000_000)


@router.post("/csv/preview", response_model=list[ErpSupplyRecord])
async def preview_csv(payload: ErpCsvPreviewPayload) -> list[ErpSupplyRecord]:
    try:
        return parse_erp_csv(payload.content)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "erp_csv_invalid", "message": str(error)},
        ) from error
