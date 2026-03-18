from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class AnalysisRunCreate(BaseModel):
    document_id: UUID
    document_file_id: UUID | None = None
    model_name: str
    model_version: str | None = None
    status: str = "pending"
    bronze_status: str | None = None
    silver_status: str | None = None
    bronze_output: dict | None = None
    silver_output: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AnalysisRunUpdate(BaseModel):
    document_file_id: UUID | None = None
    model_name: str | None = None
    model_version: str | None = None
    status: str | None = None
    bronze_status: str | None = None
    silver_status: str | None = None
    bronze_output: dict | None = None
    silver_output: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AnalysisRunRead(ORMModel):
    id: UUID
    document_id: UUID
    document_file_id: UUID | None
    model_name: str
    model_version: str | None
    status: str
    bronze_status: str | None
    silver_status: str | None
    bronze_output: dict | None
    silver_output: dict | None
    error_message: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
