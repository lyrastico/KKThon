from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampsMixin(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None


class UUIDMixin(BaseModel):
    id: UUID
