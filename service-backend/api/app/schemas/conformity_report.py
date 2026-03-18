from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ConformityReportCreate(BaseModel):
    client_id: UUID
    gold_content: dict[str, Any] | None = None
    s3_gold_path: str | None = None
    silver_content: dict[str, Any] | None = None
    processing_status: str = "pending"


class ConformityReportUpdate(BaseModel):
    gold_content: dict[str, Any] | None = None
    s3_gold_path: str | None = None
    silver_content: dict[str, Any] | None = None
    processing_status: str | None = None


class ConformityReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    report_id: UUID
    client_id: UUID
    gold_content: dict[str, Any] | None
    s3_gold_path: str | None
    silver_content: dict[str, Any] | None
    processing_status: str
    created_at: datetime
    updated_at: datetime
