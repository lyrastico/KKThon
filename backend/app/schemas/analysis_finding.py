from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import ORMModel


class AnalysisFindingCreate(BaseModel):
    analysis_run_id: UUID
    finding_type: str
    code: str
    label: str
    severity: str | None = None
    is_pass: bool | None = None
    confidence: float | None = None
    message: str | None = None
    extracted_value: dict | str | int | float | bool | None = None
    details: dict = Field(default_factory=dict)


class AnalysisFindingUpdate(BaseModel):
    finding_type: str | None = None
    code: str | None = None
    label: str | None = None
    severity: str | None = None
    is_pass: bool | None = None
    confidence: float | None = None
    message: str | None = None
    extracted_value: dict | str | int | float | bool | None = None
    details: dict | None = None


class AnalysisFindingRead(ORMModel):
    id: UUID
    analysis_run_id: UUID
    finding_type: str
    code: str
    label: str
    severity: str | None
    is_pass: bool | None
    confidence: float | None
    message: str | None
    extracted_value: dict | str | int | float | bool | None
    details: dict
    created_at: datetime
