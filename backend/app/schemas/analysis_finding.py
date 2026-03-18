from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class AnalysisFindingCreate(BaseModel):
    analysis_run_id: UUID
    code: str | None = None
    label: str | None = None
    severity: str | None = None
    status: str | None = None
    message: str | None = None
    details: dict | None = None
    field_name: str | None = None
    page_number: int | None = None


class AnalysisFindingUpdate(BaseModel):
    code: str | None = None
    label: str | None = None
    severity: str | None = None
    status: str | None = None
    message: str | None = None
    details: dict | None = None
    field_name: str | None = None
    page_number: int | None = None


class AnalysisFindingRead(ORMModel):
    id: UUID
    analysis_run_id: UUID
    code: str | None
    label: str | None
    severity: str | None
    status: str | None
    message: str | None
    details: dict | None
    field_name: str | None
    page_number: int | None
    created_at: datetime
    updated_at: datetime
