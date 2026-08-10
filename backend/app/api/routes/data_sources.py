from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.data_source import DataSourceLabel, get_data_source_label

router = APIRouter(prefix="/v1/data-sources", tags=["data-quality"])


class DataSourcePayload(BaseModel):
    source: str = Field(min_length=1)


@router.post("/label", response_model=DataSourceLabel)
async def label_source(payload: DataSourcePayload) -> DataSourceLabel:
    try:
        return get_data_source_label(payload.source)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "data_source_invalid", "message": str(error)},
        ) from error
