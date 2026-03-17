from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class SubjectConsistencyRunCreate(BaseModel):
    subject_id: UUID
    status: str = "pending"
    summary: str | None = None
    raw_result: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UUID | None = None


class SubjectConsistencyRunUpdate(BaseModel):
    status: str | None = None
    summary: str | None = None
    raw_result: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UUID | None = None


class SubjectConsistencyRunRead(ORMModel):
    id: UUID
    subject_id: UUID
    status: str
    summary: str | None
    raw_result: dict | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
