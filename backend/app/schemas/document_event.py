from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class DocumentEventCreate(BaseModel):
    document_id: UUID
    event_type: str
    message: str | None = None
    payload: dict | None = None
    created_by: UUID | None = None


class DocumentEventUpdate(BaseModel):
    event_type: str | None = None
    message: str | None = None
    payload: dict | None = None
    created_by: UUID | None = None


class DocumentEventRead(ORMModel):
    id: UUID
    document_id: UUID
    event_type: str
    message: str | None
    payload: dict | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
