from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.common import ORMModel


class SubjectCreate(BaseModel):
    organization_id: UUID
    type: str
    external_ref: str | None = None
    display_name: str
    legal_identifier: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_by: UUID | None = None


class SubjectUpdate(BaseModel):
    type: str | None = None
    external_ref: str | None = None
    display_name: str | None = None
    legal_identifier: str | None = None
    metadata: dict | None = None


class SubjectRead(ORMModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    organization_id: UUID
    type: str
    external_ref: str | None
    display_name: str
    legal_identifier: str | None
    metadata: dict = Field(alias="metadata_")
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime