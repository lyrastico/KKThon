from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.common import ORMModel


class DocumentCreate(BaseModel):
    organization_id: UUID
    subject_id: UUID
    document_type_id: UUID | None = None
    title: str
    status: str = "draft"
    compliance_status: str | None = None
    review_status: str | None = None
    uploaded_by: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    current_file_id: UUID | None = None
    latest_analysis_run_id: UUID | None = None
    compliance_status: str | None = None
    review_status: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    metadata: dict | None = None


class DocumentRead(ORMModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    organization_id: UUID
    subject_id: UUID
    document_type_id: UUID | None
    title: str
    status: str
    current_file_id: UUID | None
    latest_analysis_run_id: UUID | None
    compliance_status: str | None
    review_status: str | None
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    uploaded_by: UUID | None
    metadata: dict = Field(alias="metadata_")
    created_at: datetime
    updated_at: datetime