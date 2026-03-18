from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class SubjectFindingCreate(BaseModel):
    subject_consistency_run_id: UUID
    code: str | None = None
    label: str | None = None
    severity: str | None = None
    status: str | None = None
    message: str | None = None
    details: dict | None = None
    field_name: str | None = None


class SubjectFindingUpdate(BaseModel):
    code: str | None = None
    label: str | None = None
    severity: str | None = None
    status: str | None = None
    message: str | None = None
    details: dict | None = None
    field_name: str | None = None


class SubjectFindingRead(ORMModel):
    id: UUID
    subject_consistency_run_id: UUID
    code: str | None
    label: str | None
    severity: str | None
    status: str | None
    message: str | None
    details: dict | None
    field_name: str | None
    created_at: datetime
    updated_at: datetime
