from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ClientCreate(BaseModel):
    client_name: str


class ClientUpdate(BaseModel):
    client_name: str | None = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    client_id: UUID
    user_id: UUID
    client_name: str
    created_at: datetime
    updated_at: datetime
