from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class DocumentFileCreate(BaseModel):
    document_id: UUID
    storage_bucket: str
    storage_path: str
    original_filename: str
    mime_type: str | None = None
    extension: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    page_count: int | None = None
    version_no: int = 1
    upload_status: str = "uploaded"
    uploaded_by: UUID | None = None


class DocumentFileUpdate(BaseModel):
    storage_bucket: str | None = None
    storage_path: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    extension: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    page_count: int | None = None
    version_no: int | None = None
    upload_status: str | None = None
    uploaded_by: UUID | None = None


class DocumentFileRead(ORMModel):
    id: UUID
    document_id: UUID
    storage_bucket: str
    storage_path: str
    original_filename: str
    mime_type: str | None
    extension: str | None
    size_bytes: int | None
    sha256: str | None
    page_count: int | None
    version_no: int
    upload_status: str
    uploaded_by: UUID | None
    created_at: datetime
