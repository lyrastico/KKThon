from datetime import date, datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class SilverResultData(BaseModel):
    siren: str | None = None
    date_validite: date | None = None
    raison_sociale: str | None = None
    code_verification: str | None = None
    extractions: dict[str, Any] = Field(default_factory=dict)


class SilverResult(BaseModel):
    data: SilverResultData
    confidence_score: float | None = None
    document_detected: str | None = None
    checks: list[dict[str, Any]] = Field(default_factory=list)


class SilverSource(BaseModel):
    key: str
    bucket: str
    mime_type: str | None = None


class SilverProcessing(BaseModel):
    model: str
    processed_at: datetime | None = None


class SilverPayload(BaseModel):
    document_id: UUID
    document_file_id: UUID | None = None
    result: SilverResult
    source: SilverSource
    processing: SilverProcessing


class SilverIngestResponse(BaseModel):
    analysis_run_id: UUID
    findings_created: int


class SubjectConsistencyExecuteResponse(BaseModel):
    subject_consistency_run_id: UUID
    findings_created: int
    gold_output: dict[str, Any]
