from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class DocumentFileCreate(BaseModel):
    document_id: UUID
    storage_path: str
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    version: int | None = None
    uploaded_by: UUID | None = None


class DocumentFileUpdate(BaseModel):
    storage_path: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    version: int | None = None
    uploaded_by: UUID | None = None


class DocumentFileRead(ORMModel):
    id: UUID
    document_id: UUID
    storage_path: str
    filename: str
    mime_type: str | None
    size_bytes: int | None
    checksum: str | None
    version: int | None
    uploaded_by: UUID | None
    created_at: datetime
    updated_at: datetime
