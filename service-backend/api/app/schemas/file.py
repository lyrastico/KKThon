from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class FileCreate(BaseModel):
    client_id: UUID
    original_filename: str
    s3_raw_path: str
    file_format: str | None = None


class FileUpdate(BaseModel):
    original_filename: str | None = None
    s3_silver_path: str | None = None
    silver_content: dict[str, Any] | None = None
    file_format: str | None = None
    type: str | None = None
    processing_status: str | None = None


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    file_id: UUID
    client_id: UUID
    original_filename: str
    s3_raw_path: str
    s3_silver_path: str | None
    silver_content: dict[str, Any] | None
    file_format: str | None
    type: str | None
    processing_status: str
    created_at: datetime
    updated_at: datetime
