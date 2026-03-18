from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class AnalysisRunCreate(BaseModel):
    document_id: UUID
    run_type: str | None = None
    status: str = "pending"
    model_name: str | None = None
    summary: str | None = None
    raw_result: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UUID | None = None


class AnalysisRunUpdate(BaseModel):
    run_type: str | None = None
    status: str | None = None
    model_name: str | None = None
    summary: str | None = None
    raw_result: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UUID | None = None


class AnalysisRunRead(ORMModel):
    id: UUID
    document_id: UUID
    run_type: str | None
    status: str
    model_name: str | None
    summary: str | None
    raw_result: dict | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
